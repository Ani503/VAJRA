from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class SparePartItem(BaseModel):
    part_id: str
    part_name: str
    component: str
    base_id: str
    base_name: str
    qty_in_stock: int
    reorder_level: int
    lead_time_days: int
    unit_cost_inr_lakh: float
    supplier: str
    stock_status: str  # Nominal, Low Stock, Stockout

class SparesKPIs(BaseModel):
    total_parts: int
    below_reorder_level: int
    stockouts: int
    avg_lead_time_days: float
    pending_orders: int

class SparesOverviewResponse(BaseModel):
    matrix: Dict[str, Dict[str, int]]  # part_id -> base_id -> qty
    parts: List[SparePartItem]
    kpis: SparesKPIs

class ReorderSparesRequest(BaseModel):
    part_id: str
    base_id: str
    quantity: int
    supplier: Optional[str] = None

class TransferSparesRequest(BaseModel):
    part_id: str
    source_base_id: str
    destination_base_id: str
    quantity: int

class SparesDemandForecastItem(BaseModel):
    part_id: str
    part_name: str
    component: str
    base_id: str
    current_stock: int
    projected_failures_30d: int
    recommended_order_qty: int
    urgency: str
    estimated_cost_inr_lakh: float

class SparesDemandForecastResponse(BaseModel):
    horizon_days: int = 30
    total_projected_demand: int
    total_estimated_cost_inr_lakh: float
    forecast: List[SparesDemandForecastItem]
