
import requests
import pandas as pd
import plotly.express as px
import streamlit as st

# --------------------------------------------------
# Page configuration
# --------------------------------------------------
st.set_page_config(
    page_title="Executive Decision Intelligence",
    page_icon="📊",
    layout="wide",
)

API_BASE_URL = "http://127.0.0.1:8000/api/v1"

st.title("📊 AI Business Strategy & Executive Decision Intelligence")
st.caption(
    "Executive analytics | Sales performance | Customer satisfaction | "
    "Business recommendations"
)

# --------------------------------------------------
# API helpers
# --------------------------------------------------
@st.cache_data(ttl=30, show_spinner=False)
def fetch_api(endpoint):
    """Fetch JSON data from the FastAPI backend."""
    response = requests.get(
        f"{API_BASE_URL}/{endpoint}",
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def find_value(data, keys, default=None):
    """Find a field in nested API JSON using alternative field names."""
    if isinstance(data, dict):
        for key in keys:
            if key in data and data[key] is not None:
                return data[key]

        for value in data.values():
            result = find_value(value, keys, default=None)
            if result is not None:
                return result

    elif isinstance(data, list):
        for item in data:
            result = find_value(item, keys, default=None)
            if result is not None:
                return result

    return default


def find_list(data, keys):
    """Find a list of records in nested API JSON."""
    if isinstance(data, dict):
        for key in keys:
            value = data.get(key)
            if isinstance(value, list):
                return value

        for value in data.values():
            result = find_list(value, keys)
            if result:
                return result

    elif isinstance(data, list):
        for item in data:
            result = find_list(item, keys)
            if result:
                return result

    return []


def money(value):
    try:
        return f"₹{float(value):,.2f}"
    except (TypeError, ValueError):
        return "N/A"


def percentage(value):
    try:
        return f"{float(value):.2f}%"
    except (TypeError, ValueError):
        return "N/A"


def number(value, decimals=2):
    try:
        return f"{float(value):,.{decimals}f}"
    except (TypeError, ValueError):
        return "N/A"


def show_chart(records, title, x_candidates, y_candidates, chart_type="bar"):
    """Display a chart when matching data is available."""
    if not records:
        st.info(f"No chart data available for {title.lower()}.")
        return

    df = pd.DataFrame(records)

    x_col = next((key for key in x_candidates if key in df.columns), None)
    y_col = next((key for key in y_candidates if key in df.columns), None)

    if x_col is None or y_col is None:
        st.info(f"The API response does not contain chart fields for {title}.")
        with st.expander("Inspect available chart data"):
            st.dataframe(df, use_container_width=True)
        return

    df[y_col] = pd.to_numeric(df[y_col], errors="coerce")
    df = df.dropna(subset=[y_col])

    if df.empty:
        st.info(f"No numeric values available for {title.lower()}.")
        return

    if chart_type == "line":
        fig = px.line(
            df, x=x_col, y=y_col, markers=True, title=title
        )
    else:
        fig = px.bar(
            df, x=x_col, y=y_col, title=title, text_auto=".2s"
        )

    fig.update_layout(
        xaxis_title=x_col.replace("_", " ").title(),
        yaxis_title=y_col.replace("_", " ").title(),
        margin=dict(l=10, r=10, t=55, b=10),
    )
    st.plotly_chart(fig, use_container_width=True)


# --------------------------------------------------
# Load existing API results
# --------------------------------------------------
with st.sidebar:
    st.header("Dashboard Controls")
    st.write("Backend API")
    st.code("http://127.0.0.1:8000")
    if st.button("🔄 Refresh dashboard", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

try:
    with st.spinner("Loading business analytics from FastAPI..."):
        sales = fetch_api("analytics/sales")
        feedback = fetch_api("analytics/feedback")
        executive = fetch_api("insights/executive")

except requests.RequestException as exc:
    st.error(
        "Unable to connect to the FastAPI backend. "
        "Start the backend in your first terminal and refresh this page."
    )
    st.code(str(exc))
    st.stop()

# --------------------------------------------------
# Executive KPI cards
# --------------------------------------------------
st.subheader("Executive Overview")

# Safely extract from sales['kpis'] or top-level sales
sales_kpis = sales.get("kpis", sales)
feedback_kpis = feedback.get("kpis", feedback)

total_revenue = sales_kpis.get("total_revenue")
total_profit = sales_kpis.get("total_profit")
profit_margin = sales_kpis.get("profit_margin_percent")
average_rating = feedback_kpis.get("average_rating")
order_count = sales_kpis.get("order_count")
rating_count = feedback_kpis.get("feedback_count")

# Some APIs report the margin as a decimal rather than a percentage.
try:
    if profit_margin is not None and 0 <= float(profit_margin) <= 1:
        profit_margin = float(profit_margin) * 100
except (TypeError, ValueError):
    pass

k1, k2, k3, k4 = st.columns(4)

k1.metric("Total Revenue", money(total_revenue))
k2.metric("Total Profit", money(total_profit))
k3.metric("Profit Margin", percentage(profit_margin))
k4.metric(
    "Average Customer Rating",
    f"{number(average_rating, 2)} / 5"
    if average_rating is not None
    else "N/A",
)

if order_count is not None or rating_count is not None:
    st.caption(
        f"Orders: {order_count if order_count is not None else 'N/A'}"
        f"  |  Customer ratings: "
        f"{rating_count if rating_count is not None else 'N/A'}"
    )

# --------------------------------------------------
# Sales analytics
# --------------------------------------------------
st.divider()
st.subheader("Sales Performance")

regions = find_list(
    sales, ["region_performance", "regional_performance", "by_region", "regions"]
)
products = find_list(
    sales, ["product_performance", "product_analytics", "by_product", "products"]
)
monthly = find_list(
    sales, ["monthly_trend", "monthly_trends", "monthly_performance", "monthly"]
)

left, right = st.columns(2)

with left:
    show_chart(
        regions,
        "Revenue by Region",
        ["region", "name", "region_name"],
        ["total_revenue", "revenue", "revenue_total"],
    )

with right:
    show_chart(
        products,
        "Profit by Product",
        ["product", "product_name", "name"],
        ["total_profit", "profit", "profit_total"],
    )

show_chart(
    monthly,
    "Monthly Revenue Trend",
    ["month", "month_name", "period"],
    ["total_revenue", "revenue", "revenue_total"],
    chart_type="line",
)

with st.expander("View sales data tables"):
    if regions:
        st.markdown("**Regional performance**")
        st.dataframe(pd.DataFrame(regions), use_container_width=True)
    if products:
        st.markdown("**Product performance**")
        st.dataframe(pd.DataFrame(products), use_container_width=True)
    if monthly:
        st.markdown("**Monthly performance**")
        st.dataframe(pd.DataFrame(monthly), use_container_width=True)

# --------------------------------------------------
# Customer feedback
# --------------------------------------------------
st.divider()
st.subheader("Customer Satisfaction")

rating_distribution = feedback.get("rating_distribution", [])
segments = feedback.get("by_customer_segment", [])
feedback_regions = feedback.get("by_region", [])

c1, c2 = st.columns(2)

with c1:
    if rating_distribution:
        # rating_distribution is already a list of dicts: [{'rating': 1, 'feedback_count': 1}, ...]
        rating_df = pd.DataFrame(rating_distribution)
        if "rating" in rating_df.columns and "feedback_count" in rating_df.columns:
            rating_df["Rating"] = rating_df["rating"].astype(str)
            rating_df["Responses"] = pd.to_numeric(rating_df["feedback_count"], errors="coerce")
            
            fig = px.bar(
                rating_df,
                x="Rating",
                y="Responses",
                title="Customer Rating Distribution",
                text_auto=True,
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.dataframe(rating_df, use_container_width=True)
    else:
        st.info("Rating distribution is not available in the API response.")

with c2:
    if segments:
        segment_df = pd.DataFrame(segments)
        st.markdown("**Satisfaction by customer segment**")
        st.dataframe(segment_df, use_container_width=True)
    else:
        st.info("Customer segment data is not available.")

if feedback_regions:
    st.markdown("**Satisfaction by region**")
    st.dataframe(
        pd.DataFrame(feedback_regions),
        use_container_width=True,
    )

# --------------------------------------------------
# Executive insights and recommendations
# --------------------------------------------------
st.divider()
st.subheader("Executive Insights & Recommended Actions")

insights = find_list(
    executive, ["insights", "recommendations", "findings", "actions"]
)

if insights:
    priority_order = {"high": 0, "critical": 0, "medium": 1, "low": 2}
    insights = sorted(
        insights,
        key=lambda item: priority_order.get(
            str(item.get("priority", "low")).lower(), 3
        ),
    )

    for index, item in enumerate(insights, start=1):
        priority = str(item.get("priority", "Not specified")).upper()
        title = (
            item.get("title")
            or item.get("insight")
            or item.get("message")
            or f"Business insight {index}"
        )

        with st.expander(f"{priority} PRIORITY — {title}", expanded=(index == 1)):
            description = (
                item.get("description")
                or item.get("evidence")
                or item.get("reason")
            )
            recommendation = (
                item.get("recommendation")
                or item.get("recommended_action")
                or item.get("action")
            )

            if description:
                st.markdown(f"**Evidence / Explanation:** {description}")
            if recommendation:
                st.markdown(f"**Recommended action:** {recommendation}")

            if not description and not recommendation:
                st.json(item)
else:
    st.info("No executive insights were returned by the API.")

with st.expander("Inspect executive API response"):
    st.json(executive)

st.caption(
    "Data is supplied by the existing FastAPI analytics and rules-based "
    "insight services. Refresh to retrieve updated results."
)
