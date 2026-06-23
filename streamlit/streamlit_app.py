"""
Streamlit-in-Snowflake Dashboard — Amar Bank Workshop (Session 2).
Professional loan portfolio & customer analytics dashboard.
Deploy: Snowsight > Projects > Streamlit > + Streamlit App
"""
import streamlit as st
import pandas as pd
import altair as alt
from snowflake.snowpark.context import get_active_session

# ─────────────────────────────────────────────────────────────────────
# PAGE CONFIG & CUSTOM STYLING
# ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Amar Bank — Portfolio Intelligence",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
    }
    [data-testid="stSidebar"] * {
        color: #e0e0e0 !important;
    }
    [data-testid="stSidebar"] .stSelectbox label {
        color: #a0cfff !important;
        font-weight: 600;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.2rem 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
    }
    .metric-card h3 {
        margin: 0;
        font-size: 0.85rem;
        font-weight: 500;
        opacity: 0.85;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-card h1 {
        margin: 0.3rem 0 0 0;
        font-size: 1.8rem;
        font-weight: 700;
    }
    .metric-card-green {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        box-shadow: 0 4px 15px rgba(17, 153, 142, 0.3);
    }
    .metric-card-orange {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        box-shadow: 0 4px 15px rgba(245, 87, 108, 0.3);
    }
    .metric-card-blue {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        box-shadow: 0 4px 15px rgba(79, 172, 254, 0.3);
    }
    .section-header {
        font-size: 1.1rem;
        font-weight: 600;
        color: #1a1a2e;
        border-left: 4px solid #667eea;
        padding-left: 12px;
        margin: 1.5rem 0 1rem 0;
    }
    div[data-testid="stMetricValue"] {
        font-size: 1.5rem;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: #f0f2f6;
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
    }
    .stTabs [aria-selected="true"] {
        background-color: #667eea !important;
        color: white !important;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# DATA CONNECTION
# ─────────────────────────────────────────────────────────────────────
session = get_active_session()

@st.cache_data(ttl=600)
def query(sql: str) -> pd.DataFrame:
    return session.sql(sql).to_pandas()

loans = query("SELECT * FROM AMAR_WORKSHOP.GOLD.MART_LOAN_PERFORMANCE")
cust = query("SELECT * FROM AMAR_WORKSHOP.GOLD.MART_CUSTOMER_360")

# ─────────────────────────────────────────────────────────────────────
# SIDEBAR
# ─────────────────────────────────────────────────────────────────────
with st.sidebar:
    st.image("https://upload.wikimedia.org/wikipedia/id/4/47/Logo_Amar_Bank.png", width=160)
    st.markdown("---")
    st.markdown("### 🎛️ Filters")

    segments = ["All"] + sorted(loans["PRODUCT_SEGMENT"].unique().tolist())
    selected_segment = st.selectbox("Product Segment", segments, index=0)

    provinces = ["All"] + sorted(cust["PROVINCE"].unique().tolist())
    selected_province = st.selectbox("Province", provinces, index=0)

    dpd_options = ["All"] + sorted(loans["DPD_BUCKET"].unique().tolist())
    selected_dpd = st.selectbox("DPD Bucket", dpd_options, index=0)

    st.markdown("---")
    st.caption("🔒 Data sintetis untuk workshop")
    st.caption("Powered by Snowflake + Streamlit")

# Apply filters
filtered_loans = loans.copy()
if selected_segment != "All":
    filtered_loans = filtered_loans[filtered_loans["PRODUCT_SEGMENT"] == selected_segment]
if selected_dpd != "All":
    filtered_loans = filtered_loans[filtered_loans["DPD_BUCKET"] == selected_dpd]

filtered_cust = cust.copy()
if selected_province != "All":
    filtered_cust = filtered_cust[filtered_cust["PROVINCE"] == selected_province]
if selected_segment != "All":
    cust_ids = filtered_loans["CUSTOMER_ID"].unique()
    filtered_cust = filtered_cust[filtered_cust["CUSTOMER_ID"].isin(cust_ids)]

# ─────────────────────────────────────────────────────────────────────
# HEADER
# ─────────────────────────────────────────────────────────────────────
st.markdown("## 🏦 Amar Bank — Portfolio Intelligence Dashboard")
st.markdown("Real-time analytics platform for loan portfolio monitoring & customer insights")
st.markdown("---")

# ─────────────────────────────────────────────────────────────────────
# KPI CARDS
# ─────────────────────────────────────────────────────────────────────
total_loans = len(filtered_loans)
npl_rate = (filtered_loans["IS_DEFAULT"].mean() * 100) if total_loans > 0 else 0
total_outstanding = filtered_loans["OUTSTANDING"].sum()
total_customers = len(filtered_cust)
avg_collection = filtered_loans["COLLECTION_RATIO"].mean() * 100 if total_loans > 0 else 0

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.markdown(f"""
    <div class="metric-card">
        <h3>Total Loans</h3>
        <h1>{total_loans:,}</h1>
    </div>""", unsafe_allow_html=True)
with k2:
    st.markdown(f"""
    <div class="metric-card-orange metric-card">
        <h3>NPL Rate</h3>
        <h1>{npl_rate:.1f}%</h1>
    </div>""", unsafe_allow_html=True)
with k3:
    st.markdown(f"""
    <div class="metric-card-green metric-card">
        <h3>Outstanding</h3>
        <h1>Rp {total_outstanding/1e9:,.1f}B</h1>
    </div>""", unsafe_allow_html=True)
with k4:
    st.markdown(f"""
    <div class="metric-card-blue metric-card">
        <h3>Customers</h3>
        <h1>{total_customers:,}</h1>
    </div>""", unsafe_allow_html=True)
with k5:
    st.markdown(f"""
    <div class="metric-card metric-card-green">
        <h3>Avg Collection</h3>
        <h1>{avg_collection:.1f}%</h1>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────
# TABBED CONTENT
# ─────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Portfolio Overview",
    "⚠️ Risk & DPD Analysis",
    "👥 Customer 360",
    "📈 Trend & Collection"
])

# Color palette
COLORS = ["#667eea", "#764ba2", "#f5576c", "#4facfe", "#38ef7d", "#ffa62b"]

# ─────── TAB 1: PORTFOLIO ─────────────────────────────────────────────
with tab1:
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown('<p class="section-header">Outstanding by Product Segment</p>', unsafe_allow_html=True)
        by_seg = filtered_loans.groupby("PRODUCT_SEGMENT").agg(
            n_loans=("LOAN_ID", "count"),
            outstanding=("OUTSTANDING", "sum"),
            npl=("IS_DEFAULT", "mean"),
            avg_plafond=("PLAFOND", "mean"),
        ).reset_index()
        by_seg["npl_pct"] = (by_seg["npl"] * 100).round(2)
        by_seg["outstanding_b"] = (by_seg["outstanding"] / 1e9).round(2)

        chart_seg = alt.Chart(by_seg).mark_bar(
            cornerRadiusTopLeft=6, cornerRadiusTopRight=6
        ).encode(
            x=alt.X("PRODUCT_SEGMENT:N", title="Product Segment", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("outstanding_b:Q", title="Outstanding (Billion Rp)"),
            color=alt.Color("PRODUCT_SEGMENT:N", scale=alt.Scale(range=COLORS), legend=None),
            tooltip=[
                alt.Tooltip("PRODUCT_SEGMENT:N", title="Segment"),
                alt.Tooltip("n_loans:Q", title="Loans", format=","),
                alt.Tooltip("outstanding_b:Q", title="Outstanding (B)", format=",.2f"),
                alt.Tooltip("npl_pct:Q", title="NPL Rate %", format=".1f"),
            ]
        ).properties(height=320)
        st.altair_chart(chart_seg, use_container_width=True)

    with col_right:
        st.markdown('<p class="section-header">Portfolio Composition</p>', unsafe_allow_html=True)
        pie_seg = alt.Chart(by_seg).mark_arc(innerRadius=55, outerRadius=110, stroke="#fff", strokeWidth=2).encode(
            theta=alt.Theta("n_loans:Q"),
            color=alt.Color("PRODUCT_SEGMENT:N", scale=alt.Scale(range=COLORS),
                            legend=alt.Legend(title="Segment", orient="bottom")),
            tooltip=[
                alt.Tooltip("PRODUCT_SEGMENT:N", title="Segment"),
                alt.Tooltip("n_loans:Q", title="Loans", format=","),
                alt.Tooltip("npl_pct:Q", title="NPL %", format=".1f"),
            ]
        ).properties(height=280)
        st.altair_chart(pie_seg, use_container_width=True)

    st.markdown('<p class="section-header">Segment Performance Table</p>', unsafe_allow_html=True)
    display_seg = by_seg[["PRODUCT_SEGMENT", "n_loans", "outstanding_b", "npl_pct", "avg_plafond"]].copy()
    display_seg.columns = ["Segment", "Loans", "Outstanding (B)", "NPL Rate %", "Avg Plafond"]
    display_seg["Avg Plafond"] = display_seg["Avg Plafond"].apply(lambda x: f"Rp {x:,.0f}")
    st.dataframe(display_seg, use_container_width=True, hide_index=True)

# ─────── TAB 2: RISK / DPD ───────────────────────────────────────────
with tab2:
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<p class="section-header">Loan Distribution by DPD Bucket</p>', unsafe_allow_html=True)
        dpd_order = ["CURRENT", "DPD_1_30", "DPD_31_60", "DPD_61_90", "DPD_90_PLUS"]
        dpd_colors = ["#38ef7d", "#4facfe", "#ffa62b", "#f093fb", "#f5576c"]
        dpd = filtered_loans.groupby("DPD_BUCKET").agg(
            n_loans=("LOAN_ID", "count"),
            outstanding=("OUTSTANDING", "sum")
        ).reset_index()
        dpd["outstanding_b"] = (dpd["outstanding"] / 1e9).round(2)
        dpd["pct"] = (dpd["n_loans"] / dpd["n_loans"].sum() * 100).round(1)

        chart_dpd = alt.Chart(dpd).mark_bar(
            cornerRadiusTopLeft=6, cornerRadiusTopRight=6
        ).encode(
            x=alt.X("DPD_BUCKET:N", sort=dpd_order, title="DPD Bucket", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("n_loans:Q", title="Number of Loans"),
            color=alt.Color("DPD_BUCKET:N", sort=dpd_order,
                            scale=alt.Scale(domain=dpd_order, range=dpd_colors), legend=None),
            tooltip=[
                alt.Tooltip("DPD_BUCKET:N", title="Bucket"),
                alt.Tooltip("n_loans:Q", title="Loans", format=","),
                alt.Tooltip("pct:Q", title="% Total", format=".1f"),
                alt.Tooltip("outstanding_b:Q", title="Outstanding (B)", format=",.2f"),
            ]
        ).properties(height=320)
        st.altair_chart(chart_dpd, use_container_width=True)

    with col_right:
        st.markdown('<p class="section-header">Outstanding at Risk by DPD</p>', unsafe_allow_html=True)
        chart_dpd_out = alt.Chart(dpd).mark_arc(innerRadius=60, outerRadius=120, stroke="#fff", strokeWidth=2).encode(
            theta=alt.Theta("outstanding:Q"),
            color=alt.Color("DPD_BUCKET:N", sort=dpd_order,
                            scale=alt.Scale(domain=dpd_order, range=dpd_colors),
                            legend=alt.Legend(title="DPD Bucket", orient="bottom")),
            tooltip=[
                alt.Tooltip("DPD_BUCKET:N", title="Bucket"),
                alt.Tooltip("outstanding_b:Q", title="Outstanding (B)", format=",.2f"),
                alt.Tooltip("pct:Q", title="% Loans", format=".1f"),
            ]
        ).properties(height=320)
        st.altair_chart(chart_dpd_out, use_container_width=True)

    st.markdown('<p class="section-header">Default Analysis by Product</p>', unsafe_allow_html=True)
    default_seg = filtered_loans.groupby(["PRODUCT_SEGMENT", "DPD_BUCKET"]).agg(
        n_loans=("LOAN_ID", "count"),
        outstanding=("OUTSTANDING", "sum")
    ).reset_index()
    heatmap = alt.Chart(default_seg).mark_rect(cornerRadius=4).encode(
        x=alt.X("DPD_BUCKET:N", sort=dpd_order, title="DPD Bucket"),
        y=alt.Y("PRODUCT_SEGMENT:N", title="Product"),
        color=alt.Color("n_loans:Q", scale=alt.Scale(scheme="blues"), title="Loans"),
        tooltip=[
            alt.Tooltip("PRODUCT_SEGMENT:N"),
            alt.Tooltip("DPD_BUCKET:N"),
            alt.Tooltip("n_loans:Q", format=","),
            alt.Tooltip("outstanding:Q", format=",.0f"),
        ]
    ).properties(height=200)
    st.altair_chart(heatmap, use_container_width=True)

# ─────── TAB 3: CUSTOMER 360 ─────────────────────────────────────────
with tab3:
    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown('<p class="section-header">Customer Distribution by Province (Top 15)</p>', unsafe_allow_html=True)
        prov = filtered_cust.groupby("PROVINCE").agg(
            customers=("CUSTOMER_ID", "count"),
            savings=("TOTAL_SAVINGS_BALANCE", "sum"),
            avg_score=("CREDIT_SCORE", "mean"),
        ).reset_index().sort_values("customers", ascending=False).head(15)
        prov["savings_b"] = (prov["savings"] / 1e9).round(2)
        prov["avg_score"] = prov["avg_score"].round(0)

        chart_prov = alt.Chart(prov).mark_bar(
            cornerRadiusTopLeft=4, cornerRadiusTopRight=4
        ).encode(
            x=alt.X("customers:Q", title="Customers"),
            y=alt.Y("PROVINCE:N", sort="-x", title=""),
            color=alt.Color("customers:Q", scale=alt.Scale(scheme="purples"), legend=None),
            tooltip=[
                alt.Tooltip("PROVINCE:N", title="Province"),
                alt.Tooltip("customers:Q", title="Customers", format=","),
                alt.Tooltip("savings_b:Q", title="Savings (B)", format=",.2f"),
                alt.Tooltip("avg_score:Q", title="Avg Score", format=",.0f"),
            ]
        ).properties(height=400)
        st.altair_chart(chart_prov, use_container_width=True)

    with col_right:
        st.markdown('<p class="section-header">Customer Segment Split</p>', unsafe_allow_html=True)
        seg_cust = filtered_cust.groupby("SEGMENT").agg(
            customers=("CUSTOMER_ID", "count"),
            avg_income=("MONTHLY_INCOME", "mean"),
        ).reset_index()
        seg_cust["avg_income_m"] = (seg_cust["avg_income"] / 1e6).round(1)

        pie_cust = alt.Chart(seg_cust).mark_arc(innerRadius=50, outerRadius=100, stroke="#fff", strokeWidth=2).encode(
            theta=alt.Theta("customers:Q"),
            color=alt.Color("SEGMENT:N", scale=alt.Scale(range=["#667eea", "#38ef7d", "#f5576c"]),
                            legend=alt.Legend(title="Segment", orient="bottom")),
            tooltip=[
                alt.Tooltip("SEGMENT:N"),
                alt.Tooltip("customers:Q", format=","),
                alt.Tooltip("avg_income_m:Q", title="Avg Income (M)", format=",.1f"),
            ]
        ).properties(height=250)
        st.altair_chart(pie_cust, use_container_width=True)

        st.markdown('<p class="section-header">Credit Score Distribution</p>', unsafe_allow_html=True)
        hist_score = alt.Chart(filtered_cust).mark_bar(
            cornerRadiusTopLeft=3, cornerRadiusTopRight=3, color="#667eea", opacity=0.8
        ).encode(
            x=alt.X("CREDIT_SCORE:Q", bin=alt.Bin(maxbins=20), title="Credit Score"),
            y=alt.Y("count()", title="Customers"),
            tooltip=[alt.Tooltip("count()", title="Count")]
        ).properties(height=180)
        st.altair_chart(hist_score, use_container_width=True)

# ─────── TAB 4: TREND & COLLECTION ───────────────────────────────────
with tab4:
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<p class="section-header">Collection Ratio by Product Segment</p>', unsafe_allow_html=True)
        coll = filtered_loans[filtered_loans["COLLECTION_RATIO"].notna()].copy()
        coll_seg = coll.groupby("PRODUCT_SEGMENT").agg(
            avg_collection=("COLLECTION_RATIO", "mean"),
            median_collection=("COLLECTION_RATIO", "median"),
        ).reset_index()
        coll_seg["avg_pct"] = (coll_seg["avg_collection"] * 100).round(1)
        coll_seg["median_pct"] = (coll_seg["median_collection"] * 100).round(1)

        chart_coll = alt.Chart(coll_seg).mark_bar(
            cornerRadiusTopLeft=6, cornerRadiusTopRight=6
        ).encode(
            x=alt.X("PRODUCT_SEGMENT:N", title="", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("avg_pct:Q", title="Avg Collection Rate %", scale=alt.Scale(domain=[0, 105])),
            color=alt.Color("PRODUCT_SEGMENT:N", scale=alt.Scale(range=COLORS), legend=None),
            tooltip=[
                alt.Tooltip("PRODUCT_SEGMENT:N"),
                alt.Tooltip("avg_pct:Q", title="Avg %", format=".1f"),
                alt.Tooltip("median_pct:Q", title="Median %", format=".1f"),
            ]
        ).properties(height=300)

        rule = alt.Chart(pd.DataFrame({"y": [100]})).mark_rule(
            color="#f5576c", strokeDash=[4, 4], strokeWidth=2
        ).encode(y="y:Q")

        st.altair_chart(chart_coll + rule, use_container_width=True)

    with col_right:
        st.markdown('<p class="section-header">Disbursement Timeline</p>', unsafe_allow_html=True)
        filtered_loans["DISBURSED_MONTH"] = pd.to_datetime(filtered_loans["DISBURSED_AT"]).dt.to_period("M").astype(str)
        monthly = filtered_loans.groupby("DISBURSED_MONTH").agg(
            n_loans=("LOAN_ID", "count"),
            volume=("PLAFOND", "sum"),
        ).reset_index().sort_values("DISBURSED_MONTH")
        monthly["volume_b"] = (monthly["volume"] / 1e9).round(2)

        chart_timeline = alt.Chart(monthly).mark_area(
            line={"color": "#667eea"},
            color=alt.Gradient(
                gradient="linear",
                stops=[
                    alt.GradientStop(color="rgba(102,126,234,0.4)", offset=0),
                    alt.GradientStop(color="rgba(102,126,234,0.02)", offset=1),
                ],
                x1=1, x2=1, y1=1, y2=0
            )
        ).encode(
            x=alt.X("DISBURSED_MONTH:T", title="Month"),
            y=alt.Y("volume_b:Q", title="Disbursement Volume (B)"),
            tooltip=[
                alt.Tooltip("DISBURSED_MONTH:T", title="Month"),
                alt.Tooltip("n_loans:Q", title="Loans", format=","),
                alt.Tooltip("volume_b:Q", title="Volume (B)", format=",.2f"),
            ]
        ).properties(height=300)
        st.altair_chart(chart_timeline, use_container_width=True)

    st.markdown('<p class="section-header">Late Payment Patterns</p>', unsafe_allow_html=True)
    late = filtered_loans[filtered_loans["N_LATE"] > 0].copy()
    if len(late) > 0:
        late_seg = late.groupby("PRODUCT_SEGMENT").agg(
            avg_late=("N_LATE", "mean"),
            max_late=("MAX_DAYS_LATE", "max"),
            n_loans=("LOAN_ID", "count"),
        ).reset_index()
        late_seg["avg_late"] = late_seg["avg_late"].round(1)

        col_a, col_b, col_c = st.columns(3)
        for i, row in late_seg.iterrows():
            with [col_a, col_b, col_c][i % 3]:
                st.metric(
                    label=f"{row['PRODUCT_SEGMENT']}",
                    value=f"{row['avg_late']:.1f} avg late",
                    delta=f"Max {row['max_late']} days",
                    delta_color="inverse"
                )
    else:
        st.info("No late payments in current filter selection.")

# ─────────────────────────────────────────────────────────────────────
# FOOTER
# ─────────────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    "<div style='text-align:center; color:#888; font-size:0.85rem;'>"
    "🏦 Amar Bank Portfolio Intelligence · Built with Streamlit-in-Snowflake · "
    "Data: Synthetic (Workshop Only)</div>",
    unsafe_allow_html=True
)
