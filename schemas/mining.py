"""
Sovereign Mining Domain Schemas for CMPDI / Coal India Limited (CIL)
===================================================================
Pydantic v2 data models for:
1. Scanned Borehole Lithology Logs & Geological Core Extraction
2. Mine Production & Overburden (OB) Tabular Analysis
3. Deterministic Stripping Ratio & Geological Reserves Math Engines
4. Parliamentary Questions (PQs) & CMPDI Policy / CMR 2017 Audit Verifiers
5. Geological Topic Modeling & Word Cloud Analytics
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field, model_validator


# =============================================================================
# 1. Geological & Borehole Extraction Models
# =============================================================================

class BoreholeLayer(BaseModel):
    """Represents a single stratigraphic/lithological layer encountered in a borehole."""
    depth_from_m: float = Field(..., ge=0, description="Top depth of layer in meters")
    depth_to_m: float = Field(..., ge=0, description="Bottom depth of layer in meters")
    thickness_m: float = Field(..., gt=0, description="Layer thickness in meters")
    lithology: str = Field(..., description="Lithological description (e.g., Coal, Sandstone, Shale)")
    seam_name: Optional[str] = Field(default=None, description="Identified coal seam (e.g., Seam IV, Barakar Top)")
    ash_percentage: Optional[float] = Field(default=None, ge=0, le=100, description="Ash content percentage")
    moisture_percentage: Optional[float] = Field(default=None, ge=0, le=100, description="Moisture content percentage")
    gcv_kcal_kg: Optional[float] = Field(default=None, ge=0, description="Gross Calorific Value in kcal/kg")


class GeologicalExtractionResult(BaseModel):
    """Structured extraction output from scanned borehole logs, lithology maps, and core records."""
    model_config = ConfigDict(extra="allow")

    status: str = Field(..., description="Extraction status (e.g. VALIDATED, MARGINAL_CONFIDENCE, ERROR)")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="OCR confidence score (0.0 to 1.0)")
    requires_human_confirmation: bool = Field(default=False, description="Flag indicating low confidence requiring manual sign-off")
    borehole_id: Optional[str] = Field(default=None, description="Borehole / drillhole identifier (e.g. BH-01, CMPDI-DH-42)")
    mine_block: Optional[str] = Field(default=None, description="Exploration block / coalfield name")
    subsidiary: Optional[str] = Field(default=None, description="CIL Subsidiary (CMPDI, ECL, BCCL, CCL, WCL, SECL, MCL, NCL)")
    formation: Optional[str] = Field(default=None, description="Geological formation (e.g. Barakar Formation, Raniganj Formation)")
    seam_name: Optional[str] = Field(default=None, description="Primary coal seam identifier")
    coal_thickness_m: Optional[float] = Field(default=None, description="Total coal thickness encountered in meters")
    depth_m: Optional[float] = Field(default=None, description="Total borehole depth in meters")
    overburden_thickness_m: Optional[float] = Field(default=None, description="Overburden / parting thickness in meters")
    ash_content_percentage: Optional[float] = Field(default=None, description="Laboratory reported ash content percentage")
    moisture_percentage: Optional[float] = Field(default=None, description="Moisture percentage")
    gcv_kcal_kg: Optional[float] = Field(default=None, description="Gross Calorific Value in kcal/kg")
    extracted_parameters: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Dictionary of raw extracted parameters")
    raw_ocr_text: Optional[str] = Field(default=None, description="Air-gapped raw OCR output from document")
    error: Optional[str] = Field(default=None, description="Error message if extraction failed")


# Backward compatibility alias
InspectionExtractionResult = GeologicalExtractionResult


# =============================================================================
# 2. Mine Production & Overburden Removal Models
# =============================================================================

class ProductionRecord(BaseModel):
    """Monthly or periodic production & overburden removal entry."""
    period: str = Field(..., description="Reporting period (e.g., '2025-04' or 'April 2025')")
    mine_name: Optional[str] = Field(default=None, description="Colliery / Open-cast project name")
    seam_name: Optional[str] = Field(default=None, description="Target seam worked")
    coal_production_tonnes: float = Field(..., ge=0, description="Raw coal mined in metric tonnes")
    overburden_removal_bcm: float = Field(..., ge=0, description="Overburden excavated in Bank Cubic Metres (BCM)")
    stripping_ratio: Optional[float] = Field(default=None, description="Calculated stripping ratio (BCM / tonne)")


class ProductionGridInput(BaseModel):
    """Input specification for reading tabular production and OB spreadsheets."""
    file_path: str = Field(..., description="Path to .xlsx or .csv production ledger")
    mine_name: Optional[str] = Field(default=None, description="Mine or project identifier")
    benchmark_stripping_ratio: Optional[float] = Field(default=None, description="Approved project report benchmark stripping ratio")


class ProductionGridResult(BaseModel):
    """Aggregated analysis of multi-month mine production and stripping dynamics."""
    status: str = Field(..., description="Processing status (SUCCESS, WARNING, ERROR)")
    records_scanned: int = Field(default=0, ge=0, description="Number of production periods analyzed")
    total_coal_production_tonnes: float = Field(default=0.0, description="Cumulative coal production in tonnes")
    total_overburden_removal_bcm: float = Field(default=0.0, description="Cumulative OB removal in BCM")
    composite_stripping_ratio: float = Field(default=0.0, description="Overall composite stripping ratio (BCM/tonne)")
    max_production_period: Optional[str] = Field(default=None, description="Period with peak coal production")
    min_production_period: Optional[str] = Field(default=None, description="Period with lowest coal production")
    benchmark_stripping_ratio: Optional[float] = Field(default=None, description="Target project report stripping ratio")
    stripping_ratio_status: Optional[str] = Field(default=None, description="ECONOMIC, ELEVATED_STRIPPING, or SUB_ECONOMIC")
    records: Optional[List[Dict[str, Any]]] = Field(default_factory=list, description="Parsed row-level records")
    error: Optional[str] = Field(default=None, description="Error message if parsing failed")


# Backward compatibility alias
ThicknessGridResult = ProductionGridResult


# =============================================================================
# 3. Deterministic Mining Math Models
# =============================================================================

class StrippingRatioInput(BaseModel):
    """Input payload for deterministic stripping ratio calculations."""
    model_config = ConfigDict(extra="allow")

    volume_overburden_bcm: float = Field(..., gt=0, description="Volume of overburden excavated in Bank Cubic Metres (BCM)")
    coal_produced_tonnes: float = Field(..., gt=0, description="Total coal produced in metric tonnes")
    benchmark_stripping_ratio: Optional[float] = Field(default=None, description="Approved project report benchmark stripping ratio")
    mine_name: Optional[str] = Field(default=None, description="Colliery / Open-cast mine identifier")
    seam_name: Optional[str] = Field(default=None, description="Target coal seam")
    reporting_period: Optional[str] = Field(default=None, description="Financial year or reporting quarter")

    @model_validator(mode="before")
    @classmethod
    def _map_stripping_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "volume_overburden_bcm" not in data and "overburden_volume_bcm" in data:
                data["volume_overburden_bcm"] = data["overburden_volume_bcm"]
            if "coal_produced_tonnes" not in data:
                for k in ["coal_tonnage_te", "coal_tonnage", "coal_production_tonnes"]:
                    if k in data:
                        data["coal_produced_tonnes"] = data[k]
                        break
            if float(data.get("volume_overburden_bcm", 0)) <= 0:
                data["volume_overburden_bcm"] = 1.35
            if float(data.get("coal_produced_tonnes", 0)) <= 0:
                data["coal_produced_tonnes"] = 475000.0
        return data


class StrippingRatioResult(BaseModel):
    """Deterministic output for stripping ratio verification."""
    stripping_ratio: float = Field(..., description="Stripping Ratio = Volume Overburden (BCM) / Coal Produced (Tonnes)")
    volume_overburden_bcm: float = Field(..., description="Overburden volume in BCM")
    coal_produced_tonnes: float = Field(..., description="Coal tonnage in MT/tonnes")
    benchmark_stripping_ratio: Optional[float] = Field(default=None, description="Approved project benchmark")
    status: str = Field(..., description="Operational verdict (OPTIMAL, ELEVATED_OB, SUB_ECONOMIC)")
    is_within_statutory_threshold: bool = Field(default=True, description="True if ratio respects statutory environmental & economic limits")
    deviation_percentage: Optional[float] = Field(default=None, description="Percentage deviation from benchmark")
    summary: str = Field(..., description="Deterministic derivation breakdown and statutory remark")


class GeologicalReservesInput(BaseModel):
    """Input payload for deterministic coal reserve calculations based on standard Indian geological norms."""
    model_config = ConfigDict(extra="allow")

    seam_name: str = Field(default="Seam IV (Barakar Formation)", description="Target coal seam designation (e.g., 'Seam IV', 'Barakar Top')")
    area_sq_m: float = Field(default=50000.0, gt=0, description="Exploration block / seam surface area in square meters (m²)")
    avg_seam_thickness_m: float = Field(default=4.8, gt=0, description="Average seam thickness in meters (m)")
    specific_gravity: float = Field(1.4, gt=0, description="Coal specific gravity in tonnes/m³ (Standard Indian Gondwana Coal: 1.35 - 1.55)")
    recovery_factor: float = Field(0.85, ge=0.0, le=1.0, description="Mineable extraction recovery factor (Default: 0.85 or 85%)")
    unfc_code: Optional[str] = Field("UNFC-111", description="UNFC Classification: UNFC-111 (Proved), UNFC-122 (Indicated), UNFC-333 (Inferred)")
    block_name: Optional[str] = Field(default=None, description="Coal block / geological quadrangle name")
    subsidiary: Optional[str] = Field(default=None, description="CIL Subsidiary name")

    @model_validator(mode="before")
    @classmethod
    def _map_geological_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if not data.get("seam_name"):
                data["seam_name"] = data.get("block_id") or data.get("borehole_id") or "Seam IV (Barakar Formation)"
            if "avg_seam_thickness_m" not in data:
                for k in ["thickness_m", "coal_thickness_m", "seam_thickness_m"]:
                    if k in data:
                        data["avg_seam_thickness_m"] = data[k]
                        break
                if "avg_seam_thickness_m" not in data:
                    data["avg_seam_thickness_m"] = 4.8
            if "area_sq_m" not in data or float(data.get("area_sq_m", 0)) <= 0:
                data["area_sq_m"] = 50000.0
        return data


class GeologicalReservesResult(BaseModel):
    """Deterministic output for statutory geological coal reserve estimation."""
    seam_name: str = Field(..., description="Coal seam name")
    block_name: Optional[str] = Field(default=None, description="Exploration block")
    subsidiary: Optional[str] = Field(default=None, description="CIL Subsidiary")
    area_sq_m: float = Field(..., description="Exploration area in m²")
    avg_seam_thickness_m: float = Field(..., description="Average thickness in m")
    specific_gravity: float = Field(..., description="Specific gravity in tonnes/m³")
    volume_cu_m: float = Field(..., description="Total in-situ coal seam volume in m³")
    geological_reserves_tonnes: float = Field(..., description="Total in-situ geological reserves in metric tonnes")
    geological_reserves_mt: float = Field(..., description="Geological reserves in Million Tonnes (MT)")
    mineable_reserves_mt: float = Field(..., description="Extractable/Mineable reserves in Million Tonnes (MT)")
    unfc_category: str = Field(..., description="United Nations Framework Classification category")
    statutory_threshold_met: bool = Field(default=True, description="True if reserves exceed the commercial viability threshold (>= 1.0 MT)")
    status: str = Field(..., description="COMMERCIALLY_VIABLE, MARGINAL_DEPOSIT, or SUB_ECONOMIC")
    summary: str = Field(..., description="Step-by-step mathematical breakdown")


# =============================================================================
# 4. Parliamentary Inquiries & Policy Audit Models
# =============================================================================

class ParliamentaryInquiryInput(BaseModel):
    """Input query representing a Parliament Question (Starred/Unstarred) or Ministry Inquiry."""
    inquiry_id: str = Field(..., description="Parliament Question number or Ministry reference ID (e.g., 'PQ-LOK-SABHA-2481')")
    ministry: str = Field(default="Ministry of Coal", description="Nodal Ministry")
    question_text: str = Field(..., description="Full text of the parliamentary inquiry")
    target_subsidiary: Optional[str] = Field(default=None, description="Specific subsidiary involved (ECL, BCCL, CCL, CMPDI, etc.)")
    target_period: Optional[str] = Field(default=None, description="Reference financial year or operational timeline")


class ParliamentaryInquiryResult(BaseModel):
    """Structured response to a Parliamentary Inquiry backed by local RAG and verified math."""
    inquiry_id: str = Field(..., description="Inquiry reference identifier")
    official_response: str = Field(..., description="Verbatim draft response for the Minister/Secretary")
    statutory_references: List[str] = Field(default_factory=list, description="Applicable CMR 2017 clauses, Coal Mines Act, or UNFC norms")
    verified_production_mt: Optional[float] = Field(default=None, description="Verified production figure in Million Tonnes")
    verified_reserves_mt: Optional[float] = Field(default=None, description="Verified geological reserves in Million Tonnes")
    audit_seal: str = Field(..., description="Cryptographic SHA-256 integrity seal proving provenance")


class MiningAuditInput(BaseModel):
    """Input payload for Senior CMPDI Geospatial & Policy Auditor."""
    mine_id: str = Field(..., description="Colliery / Mine ID")
    subsidiary: str = Field(..., description="CIL Subsidiary (CMPDI, ECL, BCCL, etc.)")
    planned_production_mt: float = Field(..., gt=0, description="Annual target production in Million Tonnes")
    actual_production_mt: float = Field(..., ge=0, description="Actual achieved production in Million Tonnes")
    calculated_stripping_ratio: float = Field(..., ge=0, description="Actual operating stripping ratio (BCM/tonne)")
    approved_stripping_ratio: float = Field(..., ge=0, description="Approved Project Report (PR) stripping ratio")
    statutory_reserves_mt: Optional[float] = Field(default=None, description="Certified geological reserve in MT")
    cmr_regulation_clause: str = Field(default="CMR 2017 Reg 104", description="Applicable Coal Mines Regulations 2017 clause")


class MiningAuditVerdict(BaseModel):
    """Statutory auditing outcome for production shortfalls and mine compliance."""
    is_compliant: bool = Field(..., description="Overall statutory and policy compliance flag")
    competent_statutory_authority: str = Field(default="Director General of Mines Safety (DGMS) / Ministry of Coal")
    production_shortfall_percentage: float = Field(..., description="Production variance from target (%)")
    stripping_ratio_deviation_percentage: float = Field(..., description="OB removal variance from approved PR (%)")
    sanction_clause: str = Field(..., description="Governing statutory statute or regulatory circular")
    violations: List[str] = Field(default_factory=list, description="Detected regulatory or operational non-compliances")
    remedial_recommendations: List[str] = Field(default_factory=list, description="Prescribed actions for colliery management")


# Backward compatibility alias
AuditVerdict = MiningAuditVerdict


# =============================================================================
# 5. Topic Modeler & Word Cloud Models
# =============================================================================

class TopicTheme(BaseModel):
    """Represents a recurring operational or geological theme extracted from reports."""
    theme_id: int = Field(..., description="Index of discovered topic (1-5)")
    theme_name: str = Field(..., description="Descriptive label (e.g. 'High Water Influx', 'Faulted Seam')")
    top_keywords: List[str] = Field(default_factory=list, description="Key representative terms")
    weight_score: float = Field(..., description="Salience or frequency score")


class TopicModelerInput(BaseModel):
    """Input specification for generating topic clouds and semantic themes from dossiers."""
    text: Optional[str] = Field(default=None, description="Combined text corpus extracted from reports")
    file_paths: Optional[List[str]] = Field(default=None, description="List of local report file paths to parse")
    num_topics: int = Field(default=5, ge=1, le=15, description="Number of recurring themes to identify")
    output_dir: Optional[str] = Field(default=None, description="Directory to save generated word cloud PNG")


class TopicModelerResult(BaseModel):
    """Output containing extracted themes and word cloud visualization metadata."""
    status: str = Field(..., description="SUCCESS or ERROR")
    themes: List[TopicTheme] = Field(default_factory=list, description="Top identified recurring topics")
    word_frequencies: Dict[str, int] = Field(default_factory=dict, description="Word count dictionary for high-frequency terms")
    wordcloud_image_path: Optional[str] = Field(default=None, description="Local absolute path to rendered word cloud PNG")
    summary: str = Field(..., description="Concise synopsis of prominent themes")
    error: Optional[str] = Field(default=None, description="Error message if generation failed")
