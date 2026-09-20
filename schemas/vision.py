from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class InspectionExtractionResult(BaseModel):
    status: str
    confidence_score: float = Field(..., ge=0.0, le=1.0)
    requires_human_confirmation: bool
    extracted_parameters: Optional[Dict[str, object]] = None
    raw_ocr_text: Optional[str] = None
    error: Optional[str] = None


class ThicknessGridResult(BaseModel):
    status: str
    error: Optional[str] = None
    grid_points_scanned: Optional[int] = None
    nominal_thickness_mm: Optional[float] = None
    min_point_thickness_mm: Optional[float] = None
    max_point_thickness_mm: Optional[float] = None
    mean_thickness_mm: Optional[float] = None
    critical_coordinate: Optional[str] = None
    mean_loss_percentage: Optional[float] = None
    flaw_length_mm: Optional[float] = None
    outlier_points: Optional[List[Dict[str, object]]] = None
