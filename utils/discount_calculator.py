"""
Margin-Safe Discount Calculator
Combines Cognee margin floors + Serper competitor prices
to compute the optimal discount that clears stock without losing money.
"""
from typing import Optional


def calculate_optimal_discount(
    current_price: float,
    unit_cost: float,
    competitor_avg_price: Optional[float],
    competitor_min_price: Optional[float],
    target_clearance_pct: float = 0.70,   # we want to clear 70% of stock
    max_discount_pct: float = 40.0,
    historical_best_discount: Optional[float] = None,
) -> dict:
    """
    Computes the optimal discount for a clearance campaign.

    Logic:
    1. Floor price = unit_cost * 1.05  (5% above cost, absolute minimum)
    2. Competitor floor = min(competitor_min_price * 0.95, floor_price)
       (undercut competitor by 5% but never below cost+5%)
    3. Optimal discount = max(historical_best, competitor_based)
    4. Cap at max_discount_pct

    Returns a full breakdown for transparency to the merchant.
    """
    # Absolute floor: 5% above unit cost
    absolute_floor = round(unit_cost * 1.05, 2)

    # Competitor-informed target price
    if competitor_min_price and competitor_min_price > 0:
        competitor_target = round(competitor_min_price * 0.95, 2)  # 5% below competitor min
        competitor_target = max(competitor_target, absolute_floor)  # never below cost floor
    else:
        competitor_target = None

    # Historical best discount from Cognee
    if historical_best_discount:
        history_target = round(current_price * (1 - historical_best_discount / 100), 2)
        history_target = max(history_target, absolute_floor)
    else:
        history_target = None

    # Pick the lower of competitor & historical (more aggressive = more clearance)
    candidates = [p for p in [competitor_target, history_target] if p is not None]
    if candidates:
        optimal_price = min(candidates)
    else:
        # Default: 20% discount
        optimal_price = round(current_price * 0.80, 2)

    optimal_price = max(optimal_price, absolute_floor)

    # Calculate discount %
    discount_pct = round(((current_price - optimal_price) / current_price) * 100, 1)
    discount_pct = min(discount_pct, max_discount_pct)

    # Recalculate price after capping
    final_price = round(current_price * (1 - discount_pct / 100), 2)
    final_price = max(final_price, absolute_floor)

    # Margin at new price
    margin_at_discount = round(((final_price - unit_cost) / final_price) * 100, 1)

    return {
        "current_price": current_price,
        "unit_cost": unit_cost,
        "absolute_floor_price": absolute_floor,
        "competitor_avg_price": competitor_avg_price,
        "competitor_min_price": competitor_min_price,
        "competitor_target_price": competitor_target,
        "historical_best_discount": historical_best_discount,
        "optimal_discount_pct": discount_pct,
        "final_price": final_price,
        "margin_at_discount_pct": margin_at_discount,
        "margin_safe": margin_at_discount > 0,
        "reasoning": _build_reasoning(
            current_price, final_price, discount_pct,
            competitor_avg_price, absolute_floor, margin_at_discount
        ),
    }


def _build_reasoning(
    current_price, final_price, discount_pct,
    competitor_avg, floor_price, margin_pct
) -> str:
    parts = [f"Recommended: {discount_pct:.1f}% off (₹{current_price} → ₹{final_price})."]
    if competitor_avg:
        parts.append(f"Competitor avg: ₹{competitor_avg}. Your new price is competitive.")
    parts.append(f"Floor protected at ₹{floor_price}. Margin at discount: {margin_pct:.1f}%.")
    return " ".join(parts)


def estimate_revenue_recovery(
    quantity: int,
    final_price: float,
    expected_clearance_pct: float = 0.57,
) -> dict:
    """
    Estimates revenue if we clear expected_clearance_pct of stock.
    Default 57% is based on Cognee historical data for dairy campaigns.
    """
    units_expected_sold = round(quantity * expected_clearance_pct)
    revenue_expected    = round(units_expected_sold * final_price, 2)

    return {
        "quantity": quantity,
        "expected_clearance_pct": expected_clearance_pct,
        "units_expected_sold": units_expected_sold,
        "revenue_expected": revenue_expected,
    }
