"""
Estimate Calculation Service

Handles:
- Line item total calculation (qty × unit_cost)
- Estimate rollup totals (labor, material, subtotal)
- Margin calculation (markup on cost)
- Grand total calculation
"""

from decimal import Decimal, ROUND_HALF_UP
from typing import List
from app.models.estimate import Estimate, EstimateLineItem


def calculate_line_item_total(quantity: Decimal, unit_cost: Decimal) -> Decimal:
    """
    Calculate line item total from quantity and unit cost.

    Args:
        quantity: The quantity
        unit_cost: Cost per unit

    Returns:
        Total (quantity × unit_cost), rounded to 2 decimal places
    """
    if quantity is None or unit_cost is None:
        return Decimal("0")

    total = quantity * unit_cost
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def calculate_estimate_totals(
    labor_items: List[dict], material_items: List[dict], margin_percent: Decimal
) -> dict:
    """
    Calculate all estimate totals from line items and margin.

    Args:
        labor_items: List of labor line items with 'total' key
        material_items: List of material line items with 'total' key
        margin_percent: Margin percentage (e.g., 20 for 20%)

    Returns:
        Dictionary with:
        - labor_total
        - material_total
        - subtotal
        - margin_amount
        - total
    """
    # Sum labor items
    labor_total = sum(
        (Decimal(str(item.get("total", 0) or 0)) for item in labor_items), Decimal("0")
    )

    # Sum material items
    material_total = sum(
        (Decimal(str(item.get("total", 0) or 0)) for item in material_items),
        Decimal("0"),
    )

    # Calculate subtotal (cost)
    subtotal = labor_total + material_total

    # Calculate margin and total
    # Margin is calculated as: total = subtotal / (1 - margin_percent/100)
    # This means if margin is 20%, we sell at cost / 0.80 = 125% of cost
    # The margin_amount is then total - subtotal

    margin_decimal = Decimal(str(margin_percent or 0)) / Decimal("100")

    if margin_decimal < Decimal("1"):
        divisor = Decimal("1") - margin_decimal
        total = subtotal / divisor
    else:
        # Edge case: 100% margin doesn't make sense, just return subtotal
        total = subtotal

    margin_amount = total - subtotal

    return {
        "labor_total": labor_total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "material_total": material_total.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        "subtotal": subtotal.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
        "margin_amount": margin_amount.quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        ),
        "total": total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
    }


def recalculate_estimate(estimate: Estimate) -> Estimate:
    """
    Recalculate all totals for an estimate from its line items.

    Args:
        estimate: The Estimate model instance

    Returns:
        The updated Estimate with recalculated totals
    """
    # Calculate each line item total
    for item in estimate.line_items:
        item.total = calculate_line_item_total(
            Decimal(str(item.quantity or 0)), Decimal(str(item.unit_cost or 0))
        )

    # Build item lists
    labor_items = [
        {"total": item.total}
        for item in estimate.line_items
        if item.line_type == "labor"
    ]

    material_items = [
        {"total": item.total}
        for item in estimate.line_items
        if item.line_type == "material"
    ]

    # Calculate totals
    totals = calculate_estimate_totals(
        labor_items, material_items, Decimal(str(estimate.margin_percent or 20))
    )

    # Update estimate
    estimate.labor_total = totals["labor_total"]
    estimate.material_total = totals["material_total"]
    estimate.subtotal = totals["subtotal"]
    estimate.margin_amount = totals["margin_amount"]
    estimate.total = totals["total"]

    return estimate


def get_next_version(opportunity_id: int, db) -> int:
    """
    Get the next version number for an estimate.

    Args:
        opportunity_id: The opportunity ID
        db: Database session

    Returns:
        Next version number
    """
    from app.models.estimate import Estimate

    max_version = (
        db.query(Estimate.version)
        .filter(Estimate.opportunity_id == opportunity_id)
        .order_by(Estimate.version.desc())
        .first()
    )

    if max_version:
        return max_version[0] + 1
    return 1


def copy_estimate_to_new_version(estimate: Estimate, db) -> Estimate:
    """
    Create a new version of an estimate by copying it.

    Args:
        estimate: The source Estimate to copy
        db: Database session

    Returns:
        New Estimate with incremented version
    """
    new_version = get_next_version(estimate.opportunity_id, db)

    new_estimate = Estimate(
        opportunity_id=estimate.opportunity_id,
        version=new_version,
        name=f"Copy of v{estimate.version}",
        status="Draft",
        margin_percent=estimate.margin_percent,
        notes=estimate.notes,
        created_by_id=estimate.created_by_id,
    )

    db.add(new_estimate)
    db.flush()  # Get the new ID

    # Copy line items
    for item in estimate.line_items:
        new_item = EstimateLineItem(
            estimate_id=new_estimate.id,
            line_type=item.line_type,
            description=item.description,
            quantity=item.quantity,
            unit=item.unit,
            unit_cost=item.unit_cost,
            total=item.total,
            sort_order=item.sort_order,
            notes=item.notes,
        )
        db.add(new_item)

    db.flush()

    # Recalculate totals
    recalculate_estimate(new_estimate)

    return new_estimate
