
# app/services/insight_service.py

from datetime import datetime, timezone

from app.services.analytics_service import (
    get_feedback_analytics,
    get_sales_analytics,
)


def _percent_change(previous: float, current: float) -> float | None:
    """Calculate percentage change from a previous value."""
    if previous == 0:
        return None

    return round(((current - previous) / abs(previous)) * 100, 2)


def _insight(
    *,
    category: str,
    priority: str,
    title: str,
    evidence: dict,
    recommendation: str,
    business_impact: str,
) -> dict:
    return {
        "category": category,
        "priority": priority,
        "title": title,
        "evidence": evidence,
        "recommendation": recommendation,
        "business_impact": business_impact,
    }


def generate_executive_insights() -> dict:
    """Generate traceable management insights from processed business data."""

    sales = get_sales_analytics()
    feedback = get_feedback_analytics()

    kpis = sales["kpis"]
    regions = sales["by_region"]
    products = sales["by_product"]
    monthly = sales["monthly_trend"]

    feedback_kpis = feedback["kpis"]
    feedback_segments = feedback["by_customer_segment"]
    feedback_regions = feedback["by_region"]

    insights: list[dict] = []

    # 1. Regional profitability
    if len(regions) >= 2:
        highest_margin_region = max(
            regions,
            key=lambda row: row["profit_margin_percent"],
        )
        lowest_margin_region = min(
            regions,
            key=lambda row: row["profit_margin_percent"],
        )

        margin_gap = round(
            highest_margin_region["profit_margin_percent"]
            - lowest_margin_region["profit_margin_percent"],
            2,
        )

        if margin_gap >= 3:
            insights.append(
                _insight(
                    category="profitability",
                    priority="high",
                    title=(
                        f"Investigate profitability in "
                        f"{lowest_margin_region['region']}"
                    ),
                    evidence={
                        "lowest_margin_region": lowest_margin_region["region"],
                        "lowest_profit_margin_percent": (
                            lowest_margin_region["profit_margin_percent"]
                        ),
                        "highest_margin_region": (
                            highest_margin_region["region"]
                        ),
                        "highest_profit_margin_percent": (
                            highest_margin_region["profit_margin_percent"]
                        ),
                        "margin_gap_percentage_points": margin_gap,
                    },
                    recommendation=(
                        "Compare regional discounts, product mix, delivery "
                        "costs, and procurement costs. Validate the causes "
                        "before changing prices or budgets."
                    ),
                    business_impact=(
                        "Identifies possible opportunities to improve "
                        "regional profitability."
                    ),
                )
            )

    # 2. Product with the lowest profit margin
    if products:
        lowest_margin_product = min(
            products,
            key=lambda row: row["profit_margin_percent"],
        )

        average_product_margin = sum(
            row["profit_margin_percent"] for row in products
        ) / len(products)

        if (
            lowest_margin_product["profit_margin_percent"]
            < average_product_margin
        ):
            insights.append(
                _insight(
                    category="product_performance",
                    priority="medium",
                    title=(
                        f"Review the margin of "
                        f"{lowest_margin_product['product']}"
                    ),
                    evidence={
                        "product": lowest_margin_product["product"],
                        "revenue": lowest_margin_product["revenue"],
                        "profit": lowest_margin_product["profit"],
                        "profit_margin_percent": (
                            lowest_margin_product["profit_margin_percent"]
                        ),
                        "average_product_margin_percent": round(
                            average_product_margin, 2
                        ),
                    },
                    recommendation=(
                        "Review supplier costs, discount levels, returns, "
                        "and product-specific expenses. Consider pricing "
                        "changes only after validating the cost breakdown."
                    ),
                    business_impact=(
                        "Helps management identify products whose margins "
                        "may need attention."
                    ),
                )
            )

    # 3. Month-to-month revenue changes
    if len(monthly) >= 2:
        previous_month = monthly[-2]
        latest_month = monthly[-1]

        change = _percent_change(
            previous_month["revenue"],
            latest_month["revenue"],
        )

        if change is not None and change <= -10:
            insights.append(
                _insight(
                    category="sales_trend",
                    priority="high",
                    title="Revenue declined in the latest reported month",
                    evidence={
                        "previous_month": previous_month["month"],
                        "previous_revenue": previous_month["revenue"],
                        "latest_month": latest_month["month"],
                        "latest_revenue": latest_month["revenue"],
                        "change_percent": change,
                    },
                    recommendation=(
                        "Break down the revenue change by region, product, "
                        "order volume, and average order value. Compare "
                        "promotions and available sales pipeline data before "
                        "deciding on corrective action."
                    ),
                    business_impact=(
                        "Helps identify the drivers of a potential sales "
                        "slowdown before allocating additional resources."
                    ),
                )
            )
        elif change is not None and change >= 10:
            insights.append(
                _insight(
                    category="sales_trend",
                    priority="medium",
                    title="Revenue increased in the latest reported month",
                    evidence={
                        "previous_month": previous_month["month"],
                        "previous_revenue": previous_month["revenue"],
                        "latest_month": latest_month["month"],
                        "latest_revenue": latest_month["revenue"],
                        "change_percent": change,
                    },
                    recommendation=(
                        "Identify which regions and products contributed "
                        "to the increase. Check whether the improvement "
                        "is repeatable and whether margins were maintained."
                    ),
                    business_impact=(
                        "Helps management understand whether recent growth "
                        "can be sustained profitably."
                    ),
                )
            )

    # 4. Low customer ratings by segment
    if feedback_segments:
        lowest_rated_segment = min(
            feedback_segments,
            key=lambda row: row["average_rating"],
        )

        if lowest_rated_segment["average_rating"] < 3.0:
            insights.append(
                _insight(
                    category="customer_experience",
                    priority="high",
                    title=(
                        f"Investigate customer satisfaction in "
                        f"{lowest_rated_segment['customer_segment']}"
                    ),
                    evidence={
                        "customer_segment": (
                            lowest_rated_segment["customer_segment"]
                        ),
                        "average_rating": (
                            lowest_rated_segment["average_rating"]
                        ),
                        "feedback_count": (
                            lowest_rated_segment["feedback_count"]
                        ),
                        "overall_average_rating": (
                            feedback_kpis["average_rating"]
                        ),
                    },
                    recommendation=(
                        "Review the segment's written feedback, categorize "
                        "recurring complaints, and validate the findings "
                        "with customer support or account teams."
                    ),
                    business_impact=(
                        "Helps prioritize customer-experience investigation "
                        "where ratings are comparatively low."
                    ),
                )
            )

    # 5. Low customer ratings by region
    if feedback_regions:
        lowest_rated_region = min(
            feedback_regions,
            key=lambda row: row["average_rating"],
        )

        if lowest_rated_region["average_rating"] < 3.0:
            insights.append(
                _insight(
                    category="customer_experience",
                    priority="high",
                    title=(
                        f"Investigate customer feedback in "
                        f"{lowest_rated_region['region']}"
                    ),
                    evidence={
                        "region": lowest_rated_region["region"],
                        "average_rating": (
                            lowest_rated_region["average_rating"]
                        ),
                        "feedback_count": (
                            lowest_rated_region["feedback_count"]
                        ),
                    },
                    recommendation=(
                        "Examine individual comments and check for recurring "
                        "service, delivery, product-quality, or support issues. "
                        "Treat the rating as a signal to investigate, not "
                        "proof of a specific cause."
                    ),
                    business_impact=(
                        "Helps management identify a regional customer "
                        "experience issue that may need attention."
                    ),
                )
            )

    # 6. Data-driven anomaly review
    anomalies = sales.get("revenue_anomalies", [])

    if anomalies:
        insights.append(
            _insight(
                category="data_quality",
                priority="medium",
                title="Review unusual order revenue values",
                evidence={
                    "flagged_order_count": len(anomalies),
                    "anomaly_examples": anomalies[:5],
                },
                recommendation=(
                    "Validate flagged orders against invoices, quantities, "
                    "discounts, and source records. Do not automatically "
                    "remove them: unusual values may be legitimate."
                ),
                business_impact=(
                    "Helps identify potential data-entry or transaction "
                    "issues while preserving legitimate business activity."
                ),
            )
        )

    # Order insights by management urgency.
    priority_order = {"high": 0, "medium": 1, "low": 2}
    insights.sort(
        key=lambda item: priority_order.get(item["priority"], 3)
    )

    if not insights:
        insights.append(
            _insight(
                category="general",
                priority="low",
                title="No configured alert thresholds were triggered",
                evidence={
                    "profit_margin_percent": kpis["profit_margin_percent"],
                    "average_rating": feedback_kpis["average_rating"],
                    "anomaly_count": len(anomalies),
                },
                recommendation=(
                    "Continue monitoring performance and review the "
                    "underlying KPIs. No triggered rule does not mean "
                    "there are no business risks."
                ),
                business_impact=(
                    "Provides a monitoring baseline for the current dataset."
                ),
            )
        )

    high_priority_count = sum(
        1 for item in insights if item["priority"] == "high"
    )

    executive_summary = (
        f"Sales revenue is {kpis['total_revenue']:.2f}, with profit of "
        f"{kpis['total_profit']:.2f} and a profit margin of "
        f"{kpis['profit_margin_percent']:.2f}%. Customer feedback averages "
        f"{feedback_kpis['average_rating']:.2f} out of 5 across "
        f"{feedback_kpis['feedback_count']} valid ratings. "
        f"The rules-based engine identified {len(insights)} insight(s), "
        f"including {high_priority_count} high-priority item(s)."
    )

    return {
        "status": "success",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "method": "rules_based",
        "source_files": {
            "sales": sales["source_file"],
            "customer_feedback": feedback["source_file"],
        },
        "executive_summary": executive_summary,
        "headline_kpis": {
            "total_revenue": kpis["total_revenue"],
            "total_profit": kpis["total_profit"],
            "profit_margin_percent": kpis["profit_margin_percent"],
            "order_count": kpis["order_count"],
            "average_customer_rating": feedback_kpis["average_rating"],
            "feedback_count": feedback_kpis["feedback_count"],
        },
        "insight_count": len(insights),
        "high_priority_count": high_priority_count,
        "insights": insights,
        "limitations": [
            "Recommendations are generated using explicit rules, not an LLM.",
            "Findings depend on the selected processed CSV files.",
            "Sample datasets are small and do not establish causation.",
            "Validate evidence and business context before taking action.",
        ],
    }
