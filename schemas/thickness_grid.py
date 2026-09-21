from typing import List, Optional
from pydantic import BaseModel, Field


class ThicknessGridInput(BaseModel):
    """
    Input schema for the UT Gauge Matrix Analyzer.
    """

    file_path: str = Field(
        ...,
        description="Path to the UT thickness grid Excel or CSV file."
    )

    nominal_thickness_mm: float = Field(
        ...,
        gt=0,
        description="Nominal/design wall thickness in millimeters."
    )

    row_spacing_mm: Optional[float] = Field(
        default=None,
        gt=0,
        description="Physical spacing between grid rows in millimeters."
    )

    column_spacing_mm: Optional[float] = Field(
        default=None,
        gt=0,
        description="Physical spacing between grid columns in millimeters."
    )

    location_name: Optional[str] = Field(
        default=None,
        description="Name or identifier of the inspected vessel/component."
    )

    unit: str = Field(
        default="mm",
        description="Unit used for thickness measurements."
    )

class CriticalPoint(BaseModel):
    """
    Represents the most critical/thinnest point detected in the grid.
    """

    row: int = Field(
        ...,
        ge=1,
        description="1-based row number of the critical point."
    )

    column: int = Field(
        ...,
        ge=1,
        description="1-based column number of the critical point."
    )

    thickness_mm: float = Field(
        ...,
        gt=0,
        description="Measured thickness at the critical point."
    )

    location: Optional[str] = Field(
        default=None,
        description="Physical/component location associated with the point."
    )


class LocalizedThinning(BaseModel):
    """
    Represents a detected localized thinning/outlier region.
    """

    row: int = Field(..., ge=1)

    column: int = Field(..., ge=1)

    thickness_mm: float = Field(..., gt=0)

    loss_percentage: float = Field(..., ge=0)

    location: Optional[str] = None


class ThicknessGridOutput(BaseModel):
    """
    Output schema for the UT Gauge Matrix Analyzer.
    """

    grid_points_scanned: int = Field(
        ...,
        ge=0,
        description="Total number of valid UT measurement points scanned."
    )

    rows: int = Field(
        ...,
        ge=0,
        description="Number of rows in the thickness grid."
    )

    columns: int = Field(
        ...,
        ge=0,
        description="Number of columns in the thickness grid."
    )

    nominal_thickness_mm: float = Field(
        ...,
        gt=0,
        description="Nominal/reference wall thickness."
    )

    mean_thickness_mm: float = Field(
        ...,
        gt=0,
        description="Mean measured wall thickness across the grid."
    )

    min_point_thickness_mm: float = Field(
        ...,
        gt=0,
        description="Minimum measured wall thickness."
    )

    max_point_thickness_mm: float = Field(
        ...,
        gt=0,
        description="Maximum measured wall thickness."
    )

    mean_loss_percentage: float = Field(
        ...,
        ge=0,
        description="Mean wall thickness loss relative to nominal thickness."
    )

    max_loss_percentage: float = Field(
        ...,
        ge=0,
        description="Maximum wall thickness loss relative to nominal thickness."
    )

    critical_point: CriticalPoint = Field(
        ...,
        description="Location and measurement of the thinnest point."
    )

    localized_thinning: List[LocalizedThinning] = Field(
        default_factory=list,
        description="Detected localized thinning/outlier points."
    )

    flaw_length_mm: Optional[float] = Field(
        default=None,
        ge=0,
        description="Estimated physical length of the detected flaw/thinning region."
    )