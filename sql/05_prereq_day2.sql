-- =====================================================================
-- 05_prereq_day2.sql  |  Amar Bank Workshop  |  Prereq Day 2
--
-- Script ini MENGGANTIKAN dbt+Airflow untuk audiens Data Analyst (Day 2).
-- Jalankan SEKALI di awal sesi (sebelum Session 2/3/5/6).
-- Idempoten: boleh diulang tanpa efek samping (CREATE OR REPLACE).
--
-- Yang dilakukan:
--   1. Pastikan database, schema, warehouse, file format ada
--   2. Load data dari S3 ke BRONZE (COPY INTO)
--   3. Transformasi SILVER (staging views → tables + SCD-2 snapshot)
--   4. Transformasi GOLD (business marts)
--   5. Buat DQ gate stored procedure
--
-- TIDAK memerlukan: dbt, Airflow, atau tool eksternal apapun.
-- =====================================================================

-- =============================================================
-- 0) SETUP — Database, schemas, warehouse, file formats
-- =============================================================
CREATE WAREHOUSE IF NOT EXISTS AMAR_WORKSHOP_WH
    WAREHOUSE_SIZE = 'SMALL'
    AUTO_SUSPEND = 60
    AUTO_RESUME = TRUE
    INITIALLY_SUSPENDED = TRUE
    COMMENT = 'Amar Bank workshop warehouse (Gen2)';

CREATE DATABASE IF NOT EXISTS AMAR_WORKSHOP
    COMMENT = 'Amar Bank hands-on workshop (synthetic data only)';

USE DATABASE AMAR_WORKSHOP;

CREATE SCHEMA IF NOT EXISTS BRONZE     COMMENT = 'Raw data from S3';
CREATE SCHEMA IF NOT EXISTS SILVER     COMMENT = 'Cleaned & staged data';
CREATE SCHEMA IF NOT EXISTS GOLD       COMMENT = 'Business-ready marts';
CREATE SCHEMA IF NOT EXISTS GOVERNANCE COMMENT = 'Tags, policies, DMFs';

USE WAREHOUSE AMAR_WORKSHOP_WH;

-- File formats
CREATE OR REPLACE FILE FORMAT BRONZE.FF_CSV_NOHEADER
    TYPE = CSV
    SKIP_HEADER = 1
    FIELD_OPTIONALLY_ENCLOSED_BY = '"'
    TRIM_SPACE = TRUE
    NULL_IF = ('', 'NULL', 'null')
    ERROR_ON_COLUMN_COUNT_MISMATCH = FALSE;

-- =============================================================
-- 1) BRONZE — Stage + tables + COPY INTO
-- =============================================================
USE SCHEMA BRONZE;

CREATE OR REPLACE STAGE BRONZE.STG_S3_AMAR
    URL = 's3://ardiyan-s3-public/data/'
    DIRECTORY = (ENABLE = TRUE)
    COMMENT = 'Public S3 bucket with synthetic workshop data';

-- Bronze tables
CREATE OR REPLACE TABLE BRONZE.RAW_CUSTOMERS (
    customer_id    STRING,
    nik            STRING,
    npwp           STRING,
    full_name      STRING,
    gender         STRING,
    birth_date     DATE,
    province       STRING,
    city           STRING,
    segment        STRING,
    credit_score   NUMBER,
    monthly_income NUMBER,
    phone          STRING,
    email          STRING,
    created_at     TIMESTAMP_NTZ,
    updated_at     TIMESTAMP_NTZ,
    _loaded_at     TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE BRONZE.RAW_LOANS (
    loan_id       STRING,
    customer_id   STRING,
    product_type  STRING,
    plafond       NUMBER,
    tenor_months  NUMBER,
    interest_rate FLOAT,
    disbursed_at  DATE,
    status        STRING,
    dpd           NUMBER,
    is_default    NUMBER,
    outstanding   NUMBER,
    updated_at    TIMESTAMP_NTZ,
    _loaded_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE BRONZE.RAW_REPAYMENTS (
    repayment_id STRING,
    loan_id      STRING,
    due_date     DATE,
    paid_date    DATE,
    amount_due   NUMBER,
    amount_paid  NUMBER,
    is_late      NUMBER,
    _loaded_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE BRONZE.RAW_SAVINGS (
    account_id    STRING,
    customer_id   STRING,
    account_type  STRING,
    balance       NUMBER,
    interest_rate FLOAT,
    opened_at     DATE,
    status        STRING,
    _loaded_at    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

CREATE OR REPLACE TABLE BRONZE.RAW_TRANSACTIONS (
    txn_id       STRING,
    account_id   STRING,
    txn_type     STRING,
    channel      STRING,
    amount       NUMBER,
    txn_ts       TIMESTAMP_NTZ,
    _loaded_at   TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP()
);

-- Load data from S3
COPY INTO BRONZE.RAW_CUSTOMERS
  FROM @BRONZE.STG_S3_AMAR/customers.csv
  FILE_FORMAT = (FORMAT_NAME = BRONZE.FF_CSV_NOHEADER)
  ON_ERROR = CONTINUE;

COPY INTO BRONZE.RAW_LOANS
  FROM @BRONZE.STG_S3_AMAR/loans.csv
  FILE_FORMAT = (FORMAT_NAME = BRONZE.FF_CSV_NOHEADER)
  ON_ERROR = CONTINUE;

COPY INTO BRONZE.RAW_REPAYMENTS
  FROM @BRONZE.STG_S3_AMAR/repayments.csv
  FILE_FORMAT = (FORMAT_NAME = BRONZE.FF_CSV_NOHEADER)
  ON_ERROR = CONTINUE;

COPY INTO BRONZE.RAW_SAVINGS
  FROM @BRONZE.STG_S3_AMAR/savings.csv
  FILE_FORMAT = (FORMAT_NAME = BRONZE.FF_CSV_NOHEADER)
  ON_ERROR = CONTINUE;

COPY INTO BRONZE.RAW_TRANSACTIONS
  FROM @BRONZE.STG_S3_AMAR/transactions.csv
  FILE_FORMAT = (FORMAT_NAME = BRONZE.FF_CSV_NOHEADER)
  ON_ERROR = CONTINUE;

-- =============================================================
-- 2) SILVER — Staging tables (cleaned & enriched)
-- =============================================================
USE SCHEMA SILVER;

-- Drop views jika ada (dbt membuat views, kita butuh tables untuk governance)
DROP VIEW IF EXISTS SILVER.STG_CUSTOMERS;
DROP VIEW IF EXISTS SILVER.STG_LOANS;
DROP VIEW IF EXISTS SILVER.STG_REPAYMENTS;
DROP VIEW IF EXISTS SILVER.STG_SAVINGS;
DROP VIEW IF EXISTS SILVER.STG_TRANSACTIONS;

CREATE OR REPLACE TABLE SILVER.STG_CUSTOMERS AS
SELECT
    customer_id,
    nik,
    NULLIF(npwp, '')                              AS npwp,
    INITCAP(full_name)                            AS full_name,
    UPPER(gender)                                 AS gender,
    birth_date,
    DATEDIFF('year', birth_date, CURRENT_DATE())  AS age,
    province,
    city,
    segment,
    credit_score,
    monthly_income,
    phone,
    LOWER(email)                                  AS email,
    created_at,
    updated_at,
    _loaded_at
FROM BRONZE.RAW_CUSTOMERS
WHERE customer_id IS NOT NULL;

CREATE OR REPLACE TABLE SILVER.STG_LOANS AS
SELECT
    loan_id,
    customer_id,
    product_type,
    CASE
        WHEN product_type ILIKE 'Tunaiku%' THEN 'Tunaiku'
        WHEN product_type ILIKE 'SMB%'     THEN 'SMB'
        ELSE 'Other'
    END                                           AS product_segment,
    plafond,
    tenor_months,
    interest_rate,
    disbursed_at,
    status,
    dpd,
    is_default,
    CASE
        WHEN dpd = 0   THEN 'CURRENT'
        WHEN dpd <= 30 THEN 'DPD_1_30'
        WHEN dpd <= 60 THEN 'DPD_31_60'
        WHEN dpd <= 90 THEN 'DPD_61_90'
        ELSE 'DPD_90_PLUS'
    END                                           AS dpd_bucket,
    outstanding,
    updated_at,
    _loaded_at
FROM BRONZE.RAW_LOANS
WHERE loan_id IS NOT NULL;

CREATE OR REPLACE TABLE SILVER.STG_REPAYMENTS AS
SELECT
    repayment_id,
    loan_id,
    due_date,
    paid_date,
    amount_due,
    amount_paid,
    amount_due - amount_paid                      AS shortfall,
    DATEDIFF('day', due_date, paid_date)          AS days_late,
    is_late,
    _loaded_at
FROM BRONZE.RAW_REPAYMENTS
WHERE repayment_id IS NOT NULL;

CREATE OR REPLACE TABLE SILVER.STG_SAVINGS AS
SELECT
    account_id,
    customer_id,
    account_type,
    balance,
    interest_rate,
    opened_at,
    status,
    _loaded_at
FROM BRONZE.RAW_SAVINGS
WHERE account_id IS NOT NULL;

CREATE OR REPLACE TABLE SILVER.STG_TRANSACTIONS AS
SELECT
    txn_id,
    account_id,
    txn_type,
    channel,
    amount,
    txn_ts,
    DATE_TRUNC('month', txn_ts)                   AS txn_month,
    _loaded_at
FROM BRONZE.RAW_TRANSACTIONS
WHERE txn_id IS NOT NULL;

-- SCD Type-2 snapshot (simplified — one-time capture for Day 2)
CREATE OR REPLACE TABLE SILVER.DIM_CUSTOMERS_SCD2 AS
SELECT
    customer_id,
    nik,
    full_name,
    province,
    city,
    segment,
    credit_score,
    monthly_income,
    updated_at,
    updated_at                  AS dbt_valid_from,
    NULL::TIMESTAMP_NTZ         AS dbt_valid_to,
    MD5(customer_id || '|' || province || '|' || city || '|' || segment
        || '|' || credit_score::STRING || '|' || monthly_income::STRING) AS dbt_scd_id,
    CURRENT_TIMESTAMP()         AS dbt_updated_at
FROM BRONZE.RAW_CUSTOMERS
WHERE customer_id IS NOT NULL;

-- =============================================================
-- 3) GOLD — Business marts
-- =============================================================
USE SCHEMA GOLD;

CREATE OR REPLACE TABLE GOLD.MART_LOAN_PERFORMANCE AS
WITH loans AS (
    SELECT * FROM SILVER.STG_LOANS
),
repay AS (
    SELECT
        loan_id,
        COUNT(*)                         AS n_installments,
        SUM(amount_due)                  AS total_due,
        SUM(amount_paid)                 AS total_paid,
        SUM(is_late)                     AS n_late,
        MAX(days_late)                   AS max_days_late
    FROM SILVER.STG_REPAYMENTS
    GROUP BY loan_id
)
SELECT
    l.loan_id,
    l.customer_id,
    l.product_segment,
    l.product_type,
    l.status,
    l.dpd,
    l.dpd_bucket,
    l.is_default,
    l.plafond,
    l.outstanding,
    l.interest_rate,
    l.disbursed_at,
    COALESCE(r.n_installments, 0)        AS n_installments,
    COALESCE(r.total_due, 0)             AS total_due,
    COALESCE(r.total_paid, 0)            AS total_paid,
    COALESCE(r.n_late, 0)                AS n_late,
    COALESCE(r.max_days_late, 0)         AS max_days_late,
    CASE WHEN r.total_due > 0
         THEN ROUND(r.total_paid / r.total_due, 4) ELSE NULL END AS collection_ratio
FROM loans l
LEFT JOIN repay r ON l.loan_id = r.loan_id;

CREATE OR REPLACE TABLE GOLD.MART_CUSTOMER_360 AS
WITH cust AS (
    SELECT * FROM SILVER.STG_CUSTOMERS
),
loans AS (
    SELECT
        customer_id,
        COUNT(*)                 AS n_loans,
        SUM(plafond)             AS total_plafond,
        SUM(outstanding)         AS total_outstanding,
        MAX(is_default)          AS ever_default
    FROM SILVER.STG_LOANS
    GROUP BY customer_id
),
sav AS (
    SELECT
        customer_id,
        COUNT(*)                 AS n_accounts,
        SUM(balance)             AS total_balance
    FROM SILVER.STG_SAVINGS
    GROUP BY customer_id
),
txn AS (
    SELECT
        s.customer_id,
        COUNT(*)                 AS n_txn,
        SUM(t.amount)            AS total_txn_amount
    FROM SILVER.STG_TRANSACTIONS t
    JOIN SILVER.STG_SAVINGS s ON t.account_id = s.account_id
    GROUP BY s.customer_id
)
SELECT
    c.customer_id,
    c.full_name,
    c.segment,
    c.province,
    c.city,
    c.age,
    c.credit_score,
    c.monthly_income,
    COALESCE(l.n_loans, 0)            AS n_loans,
    COALESCE(l.total_plafond, 0)      AS total_plafond,
    COALESCE(l.total_outstanding, 0)  AS total_outstanding,
    COALESCE(l.ever_default, 0)       AS ever_default,
    COALESCE(sv.n_accounts, 0)        AS n_savings_accounts,
    COALESCE(sv.total_balance, 0)     AS total_savings_balance,
    COALESCE(tx.n_txn, 0)             AS n_transactions,
    COALESCE(tx.total_txn_amount, 0)  AS total_txn_amount
FROM cust c
LEFT JOIN loans l  ON c.customer_id = l.customer_id
LEFT JOIN sav   sv ON c.customer_id = sv.customer_id
LEFT JOIN txn   tx ON c.customer_id = tx.customer_id;

-- =============================================================
-- 4) DQ Gate stored procedure (Session 2 Airflow pipe references this)
-- =============================================================
CREATE OR REPLACE PROCEDURE GOLD.SP_DQ_GATE()
RETURNS VARIANT
LANGUAGE SQL
AS
$$
DECLARE
    bad_nik       INT;
    bad_score     INT;
    dup_customer  INT;
    null_segment  INT;
    orphan_loans  INT;
    verdict       VARIANT;
    total_issues  INT;
BEGIN
    SELECT COUNT(*) INTO :bad_nik
      FROM SILVER.STG_CUSTOMERS WHERE LENGTH(nik) <> 16 OR NOT nik RLIKE '^[0-9]+$';
    SELECT COUNT(*) INTO :bad_score
      FROM SILVER.STG_CUSTOMERS WHERE credit_score < 300 OR credit_score > 850;
    SELECT COUNT(*) INTO :dup_customer FROM (
        SELECT customer_id FROM SILVER.STG_CUSTOMERS GROUP BY customer_id HAVING COUNT(*) > 1
    );
    SELECT COUNT(*) INTO :null_segment
      FROM SILVER.STG_CUSTOMERS WHERE segment IS NULL OR segment = '';
    SELECT COUNT(*) INTO :orphan_loans
      FROM SILVER.STG_LOANS l
      LEFT JOIN SILVER.STG_CUSTOMERS c ON l.customer_id = c.customer_id
      WHERE c.customer_id IS NULL;

    total_issues := :bad_nik + :bad_score + :dup_customer + :null_segment + :orphan_loans;

    verdict := OBJECT_CONSTRUCT(
        'checked_at', CURRENT_TIMESTAMP()::STRING,
        'bad_nik', :bad_nik,
        'bad_credit_score', :bad_score,
        'duplicate_customer_id', :dup_customer,
        'null_segment', :null_segment,
        'orphan_loans', :orphan_loans,
        'total_issues', :total_issues,
        'status', IFF(:total_issues = 0, 'PASS', 'FAIL')
    );
    RETURN :verdict;
END;
$$;

-- =============================================================
-- 5) VERIFIKASI — cek row counts
-- =============================================================
SELECT 'BRONZE.RAW_CUSTOMERS'    AS tabel, COUNT(*) AS cnt FROM BRONZE.RAW_CUSTOMERS
UNION ALL SELECT 'BRONZE.RAW_LOANS',        COUNT(*) FROM BRONZE.RAW_LOANS
UNION ALL SELECT 'BRONZE.RAW_REPAYMENTS',   COUNT(*) FROM BRONZE.RAW_REPAYMENTS
UNION ALL SELECT 'BRONZE.RAW_SAVINGS',      COUNT(*) FROM BRONZE.RAW_SAVINGS
UNION ALL SELECT 'BRONZE.RAW_TRANSACTIONS', COUNT(*) FROM BRONZE.RAW_TRANSACTIONS
UNION ALL SELECT 'SILVER.STG_CUSTOMERS',    COUNT(*) FROM SILVER.STG_CUSTOMERS
UNION ALL SELECT 'SILVER.STG_LOANS',        COUNT(*) FROM SILVER.STG_LOANS
UNION ALL SELECT 'SILVER.STG_REPAYMENTS',   COUNT(*) FROM SILVER.STG_REPAYMENTS
UNION ALL SELECT 'SILVER.STG_SAVINGS',      COUNT(*) FROM SILVER.STG_SAVINGS
UNION ALL SELECT 'SILVER.STG_TRANSACTIONS', COUNT(*) FROM SILVER.STG_TRANSACTIONS
UNION ALL SELECT 'SILVER.DIM_CUSTOMERS_SCD2', COUNT(*) FROM SILVER.DIM_CUSTOMERS_SCD2
UNION ALL SELECT 'GOLD.MART_LOAN_PERFORMANCE', COUNT(*) FROM GOLD.MART_LOAN_PERFORMANCE
UNION ALL SELECT 'GOLD.MART_CUSTOMER_360',  COUNT(*) FROM GOLD.MART_CUSTOMER_360
ORDER BY 1;

-- DQ Gate test
CALL GOLD.SP_DQ_GATE();

-- ✅ Selesai! Semua objek siap untuk Session 2, 3, 5, dan 6.
-- Lanjutkan ke GUIDE_SESSION2_ANALYTICS.md
