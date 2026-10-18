from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.database import get_db
from backend.app.core.auth import require_any_authenticated, require_maintenance_or_above
from backend.app.models import (
    SparesInventory,
    SpareOrder,
    BaseAgency,
    EngineHealthStatus,
    Engine,
    Aircraft,
)
from backend.app.schemas.spare import (
    SparesOverviewResponse,
    SparePartItem,
    SparesKPIs,
    ReorderSparesRequest,
    TransferSparesRequest,
    SparesDemandForecastResponse,
    SparesDemandForecastItem,
)
from backend.app.services.audit import log_audit

router = APIRouter(prefix="/spares", tags=["Spares & Logistics"])

COMPONENT_PART_MAP = {
    "Fan": "PRT-001",                 # Fan Blade Set
    "Compressor": "PRT-002",          # Compressor Rotor
    "Combustion Chamber": "PRT-003",  # Combustor Liner
    "Turbine": "PRT-004",             # Turbine Blade Set
    "Shaft": "PRT-005",               # Main Shaft Bearing
}

@router.get("", response_model=SparesOverviewResponse)
def get_spares_overview(
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    inventory = db.query(SparesInventory).all()
    bases = {b.base_id: b.base_name for b in db.query(BaseAgency).all()}
    pending_orders_count = db.query(SpareOrder).filter(SpareOrder.status.in_(["Placed", "In Transit"])).count()

    matrix: Dict[str, Dict[str, int]] = {}
    part_items: List[SparePartItem] = []

    below_reorder = 0
    stockouts = 0
    total_lead_time = 0

    for item in inventory:
        matrix.setdefault(item.part_id, {})[item.base_id] = item.qty_in_stock

        if item.qty_in_stock == 0:
            stockouts += 1
            stock_status = "Stockout"
        elif item.qty_in_stock <= item.reorder_level:
            below_reorder += 1
            stock_status = "Low Stock"
        else:
            stock_status = "Nominal"

        total_lead_time += item.lead_time_days

        part_items.append(SparePartItem(
            part_id=item.part_id,
            part_name=item.part_name,
            component=item.component,
            base_id=item.base_id,
            base_name=bases.get(item.base_id, item.base_id),
            qty_in_stock=item.qty_in_stock,
            reorder_level=item.reorder_level,
            lead_time_days=item.lead_time_days,
            unit_cost_inr_lakh=item.unit_cost_inr_lakh,
            supplier=item.supplier,
            stock_status=stock_status,
        ))

    avg_lead_time = round(total_lead_time / max(1, len(inventory)), 1)

    kpis = SparesKPIs(
        total_parts=len(inventory),
        below_reorder_level=below_reorder,
        stockouts=stockouts,
        avg_lead_time_days=avg_lead_time,
        pending_orders=pending_orders_count,
    )

    return SparesOverviewResponse(
        matrix=matrix,
        parts=part_items,
        kpis=kpis,
    )

@router.post("/reorder")
def reorder_spares(
    req: ReorderSparesRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    if req.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reorder quantity must be positive")

    spare_item = db.query(SparesInventory).filter(
        SparesInventory.part_id == req.part_id,
        SparesInventory.base_id == req.base_id,
    ).first()

    if not spare_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Part {req.part_id} at {req.base_id} not found")

    supplier = req.supplier or spare_item.supplier
    order_id = f"ORD-{datetime.now().year}-{db.query(SpareOrder).count() + 1:04d}"
    order_date_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    expected_delivery = (datetime.now() + timedelta(days=spare_item.lead_time_days)).strftime("%Y-%m-%d")
    total_cost = round(req.quantity * spare_item.unit_cost_inr_lakh, 2)

    new_order = SpareOrder(
        order_id=order_id,
        part_id=req.part_id,
        base_id=req.base_id,
        quantity=req.quantity,
        status="Placed",
        order_date=order_date_str,
        expected_delivery=expected_delivery,
        supplier=supplier,
        total_cost_inr_lakh=total_cost,
    )
    db.add(new_order)
    db.commit()

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "REORDER_SPARES",
        "SPARE_ORDER",
        order_id,
        f"Placed order for {req.quantity} x {spare_item.part_name} at {req.base_id} (Total INR {total_cost} Lakh)",
    )

    return {
        "status": "success",
        "order_id": order_id,
        "part_id": req.part_id,
        "base_id": req.base_id,
        "quantity": req.quantity,
        "expected_delivery": expected_delivery,
        "total_cost_inr_lakh": total_cost,
    }

@router.post("/transfer")
def transfer_spares(
    req: TransferSparesRequest,
    db: Session = Depends(get_db),
    current_user = Depends(require_maintenance_or_above),
):
    if req.quantity <= 0:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Transfer quantity must be positive")
    if req.source_base_id == req.destination_base_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Source and destination bases cannot be identical")

    source_item = db.query(SparesInventory).filter(
        SparesInventory.part_id == req.part_id,
        SparesInventory.base_id == req.source_base_id,
    ).first()

    if not source_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Part {req.part_id} not registered at {req.source_base_id}")

    # Validate sufficient inventory
    if source_item.qty_in_stock < req.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient inventory at {req.source_base_id}. Available: {source_item.qty_in_stock}, Requested: {req.quantity}",
        )

    dest_item = db.query(SparesInventory).filter(
        SparesInventory.part_id == req.part_id,
        SparesInventory.base_id == req.destination_base_id,
    ).first()

    # Deduct from source
    source_item.qty_in_stock -= req.quantity

    # Add to destination
    if dest_item:
        dest_item.qty_in_stock += req.quantity
    else:
        # Create inventory row at destination if not previously present
        dest_item = SparesInventory(
            part_id=source_item.part_id,
            base_id=req.destination_base_id,
            part_name=source_item.part_name,
            component=source_item.component,
            qty_in_stock=req.quantity,
            reorder_level=source_item.reorder_level,
            lead_time_days=source_item.lead_time_days,
            unit_cost_inr_lakh=source_item.unit_cost_inr_lakh,
            supplier=source_item.supplier,
        )
        db.add(dest_item)

    db.commit()

    log_audit(
        db,
        current_user.service_id,
        current_user.role,
        "TRANSFER_SPARES",
        "SPARES_INVENTORY",
        req.part_id,
        f"Transferred {req.quantity} x {source_item.part_name} from {req.source_base_id} to {req.destination_base_id}",
    )

    return {
        "status": "success",
        "part_id": req.part_id,
        "source_base_id": req.source_base_id,
        "destination_base_id": req.destination_base_id,
        "transferred_quantity": req.quantity,
        "source_new_stock": source_item.qty_in_stock,
        "destination_new_stock": dest_item.qty_in_stock,
    }

@router.get("/demand-forecast", response_model=SparesDemandForecastResponse)
def get_spares_demand_forecast(
    horizon_days: int = Query(30, ge=7, le=90),
    db: Session = Depends(get_db),
    current_user = Depends(require_any_authenticated),
):
    """
    30-Day Spares Demand Forecast:
    Predicts required spare parts driven by current predicted RUL, degradation rates,
    and component mapping of engines deployed across bases.
    """
    health_records = db.query(EngineHealthStatus).all()
    engines_map = {e.engine_id: e for e in db.query(Engine).all()}
    aircraft_map = {a.aircraft_id: a for a in db.query(Aircraft).all()}
    inventory = {(s.base_id, s.part_id): s for s in db.query(SparesInventory).all()}

    # Group expected failures in next horizon_days
    # Engines with RUL <= horizon_days (assuming 1 cycle ~ 1-1.5 operating days)
    demand_counts = {}  # (base_id, component) -> count

    for h in health_records:
        rul = h.predicted_rul_cycles
        # Estimated cycles in horizon_days is roughly horizon_days * 0.8
        cycles_budget = int(horizon_days * 0.8)
        if rul <= cycles_budget:
            eng = engines_map.get(h.engine_id)
            if eng:
                air = aircraft_map.get(eng.aircraft_id)
                base_id = air.base_id if air else "BASE01"

                # Identify likely failed component
                if h.health_score < 30:
                    likely_comps = ["Turbine", "Shaft"]
                elif h.health_score < 55:
                    likely_comps = ["Combustion Chamber", "Compressor"]
                else:
                    likely_comps = ["Fan"]

                for c in likely_comps:
                    key = (base_id, c)
                    demand_counts[key] = demand_counts.get(key, 0) + 1

    forecast_items = []
    total_projected_demand = 0
    total_cost = 0.0

    for (base_id, comp), projected_count in demand_counts.items():
        part_id = COMPONENT_PART_MAP.get(comp, "PRT-001")
        item = inventory.get((base_id, part_id))
        curr_stock = item.qty_in_stock if item else 0
        part_name = item.part_name if item else comp
        unit_cost = item.unit_cost_inr_lakh if item else 5.0

        recommended_order = max(0, (projected_count + 1) - curr_stock)
        subtotal_cost = round(recommended_order * unit_cost, 2)

        urgency = "Immediate" if curr_stock == 0 else ("Within 14 Days" if curr_stock < projected_count else "Routine")

        total_projected_demand += projected_count
        total_cost += subtotal_cost

        forecast_items.append(SparesDemandForecastItem(
            part_id=part_id,
            part_name=part_name,
            component=comp,
            base_id=base_id,
            current_stock=curr_stock,
            projected_failures_30d=projected_count,
            recommended_order_qty=recommended_order,
            urgency=urgency,
            estimated_cost_inr_lakh=subtotal_cost,
        ))

    # Sort descending by urgency and projected demand
    urgency_order = {"Immediate": 0, "Within 14 Days": 1, "Routine": 2}
    forecast_items.sort(key=lambda x: (urgency_order.get(x.urgency, 3), -x.projected_failures_30d))

    return SparesDemandForecastResponse(
        horizon_days=horizon_days,
        total_projected_demand=total_projected_demand,
        total_estimated_cost_inr_lakh=round(total_cost, 2),
        forecast=forecast_items,
    )
