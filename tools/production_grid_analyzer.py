"""
Production Grid Analyzer for CMPDI / Coal India Limited (CIL)
=============================================================
Parses tabular Excel/CSV spreadsheets representing monthly coal seam production
and overburden (OB) excavation. Computes period-level stripping ratios, cumulative
reserves extracted, benchmark variances, and operational anomalies.

Supports: .xlsx, .xls, .csv
"""

import sys
import os
import csv
import logging
from typing import Optional, List, Dict, Any

# Ensure workspace root is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.mining import ProductionGridResult, ProductionRecord
from tools.audit_trail import AuditLedger

try:
    import openpyxl
except ImportError:
    openpyxl = None

try:
    import pandas as pd
except ImportError:
    pd = None

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class ProductionGridAnalyzer:
    """
    Ingests monthly/quarterly coal production and overburden spreadsheets (.xlsx, .csv).
    Computes cumulative extraction metrics, composite stripping ratios, and bench variances.
    """

    def __init__(self, benchmark_stripping_ratio: Optional[float] = None, use_audit_trail: bool = True):
        self.benchmark_sr = benchmark_stripping_ratio
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def _parse_tabular_data(self, file_path: str) -> List[Dict[str, Any]]:
        """Parses CSV or Excel file into a normalized list of dictionary records."""
        ext = os.path.splitext(file_path)[1].lower()

        if pd is not None:
            try:
                if ext == '.csv':
                    df = pd.read_csv(file_path)
                elif ext in ['.xlsx', '.xls']:
                    df = pd.read_excel(file_path)
                else:
                    raise ValueError(f"Unsupported spreadsheet format: {ext}")

                # Clean column headers
                df.columns = [str(c).strip().lower() for c in df.columns]
                records = []

                # Find header keys heuristically
                period_col = next((c for c in df.columns if any(k in c for k in ['period', 'month', 'date', 'year'])), None)
                coal_col = next((c for c in df.columns if any(k in c for k in ['coal', 'production', 'tonnes', 'te'])), None)
                ob_col = next((c for c in df.columns if any(k in c for k in ['overburden', 'ob', 'bcm', 'cu.m'])), None)
                seam_col = next((c for c in df.columns if 'seam' in c), None)

                for idx, row in df.iterrows():
                    period = str(row[period_col]) if period_col else f"Period-{idx+1}"
                    try:
                        coal = float(row[coal_col]) if coal_col and pd.notna(row[coal_col]) else 0.0
                    except (ValueError, TypeError):
                        coal = 0.0
                    try:
                        ob = float(row[ob_col]) if ob_col and pd.notna(row[ob_col]) else 0.0
                    except (ValueError, TypeError):
                        ob = 0.0

                    seam = str(row[seam_col]) if seam_col and pd.notna(row[seam_col]) else "Primary Seam"

                    if coal > 0 or ob > 0:
                        sr = round(ob / coal, 4) if coal > 0 else 0.0
                        records.append({
                            "period": period,
                            "seam_name": seam,
                            "coal_production_tonnes": coal,
                            "overburden_removal_bcm": ob,
                            "stripping_ratio": sr
                        })
                if records:
                    return records
            except Exception as e:
                logger.warning(f"Pandas parsing failed, falling back to manual reader: {e}")

        # Fallback manual parsing for CSV / OpenPyXL
        records = []
        if ext == '.csv':
            with open(file_path, 'r', newline='', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
                if len(rows) > 1:
                    headers = [c.strip().lower() for c in rows[0]]
                    p_idx = next((i for i, h in enumerate(headers) if any(k in h for k in ['month', 'period', 'date'])), 0)
                    c_idx = next((i for i, h in enumerate(headers) if any(k in h for k in ['coal', 'prod', 'tonnes'])), 1)
                    o_idx = next((i for i, h in enumerate(headers) if any(k in h for k in ['overburden', 'ob', 'bcm'])), 2)

                    for r in rows[1:]:
                        if len(r) > max(p_idx, c_idx, o_idx):
                            try:
                                coal = float(r[c_idx].strip())
                                ob = float(r[o_idx].strip())
                                sr = round(ob / coal, 4) if coal > 0 else 0.0
                                records.append({
                                    "period": r[p_idx].strip(),
                                    "coal_production_tonnes": coal,
                                    "overburden_removal_bcm": ob,
                                    "stripping_ratio": sr
                                })
                            except (ValueError, IndexError):
                                continue
        return records

    def analyze(self, file_path: str, caller_agent: str = "vision_agent") -> ProductionGridResult:
        """
        Analyzes monthly production and overburden ledger spreadsheet.
        Computes composite stripping ratios and operational flags.
        """
        if not os.path.exists(file_path):
            result = ProductionGridResult(
                status="ERROR",
                error=f"Spreadsheet file not found: {file_path}"
            )
            return self._log_and_return(result, file_path, caller_agent, "FAILED")

        records = self._parse_tabular_data(file_path)

        if not records:
            # Generate simulated standard structure if spreadsheet contains numeric matrix
            result = ProductionGridResult(
                status="NO_DATA_EXTRACTED",
                error="Could not parse recognized coal production and overburden columns."
            )
            return self._log_and_return(result, file_path, caller_agent, "FAILED")

        total_coal = sum(r["coal_production_tonnes"] for r in records)
        total_ob = sum(r["overburden_removal_bcm"] for r in records)
        composite_sr = round(total_ob / total_coal, 4) if total_coal > 0 else 0.0

        max_period_rec = max(records, key=lambda x: x["coal_production_tonnes"], default=None)
        min_period_rec = min(records, key=lambda x: x["coal_production_tonnes"], default=None)

        max_period = max_period_rec["period"] if max_period_rec else None
        min_period = min_period_rec["period"] if min_period_rec else None

        # Benchmark comparison
        if self.benchmark_sr and self.benchmark_sr > 0:
            if composite_sr <= self.benchmark_sr * 1.05:
                status_flag = "ECONOMIC_OPTIMAL"
            elif composite_sr <= self.benchmark_sr * 1.25:
                status_flag = "ELEVATED_STRIPPING_WARNING"
            else:
                status_flag = "SUB_ECONOMIC_CRITICAL"
        else:
            status_flag = "ECONOMIC_OPTIMAL" if composite_sr <= 5.5 else "ELEVATED_STRIPPING"

        result = ProductionGridResult(
            status="SUCCESS",
            records_scanned=len(records),
            total_coal_production_tonnes=round(total_coal, 2),
            total_overburden_removal_bcm=round(total_ob, 2),
            composite_stripping_ratio=composite_sr,
            max_production_period=max_period,
            min_production_period=min_period,
            benchmark_stripping_ratio=self.benchmark_sr,
            stripping_ratio_status=status_flag,
            records=records[:50]  # Store top 50 in summary
        )

        return self._log_and_return(result, file_path, caller_agent, "COMPLETED")

    def _log_and_return(self, result: ProductionGridResult, file_path: str, caller_agent: str, status: str) -> ProductionGridResult:
        if self.use_audit_trail:
            file_hash = AuditLedger.hash_artifact(file_path) or "FILE_NOT_FOUND"
            self.ledger.append_event(
                event_type="PRODUCTION_ANALYSIS",
                workflow_id="MINE_PRODUCTION_ANALYSIS",
                tool_name="production_grid_analyzer",
                caller=caller_agent,
                agent_version="2.0.0",
                tool_version="2.0.0",
                inputs={"file_path": file_path, "file_hash": file_hash, "benchmark_sr": self.benchmark_sr},
                outputs=result.model_dump(),
                status=status
            )
        return result


# Backward compatibility class alias
ThicknessGridAnalyzer = ProductionGridAnalyzer


# =============================================================================
# LangChain Tool Wrappers
# =============================================================================

from langchain_core.tools import tool
from pydantic import BaseModel, Field

class ProductionInput(BaseModel):
    file_path: str = Field(..., description="Path to .xlsx or .csv monthly production & OB spreadsheet")
    benchmark_stripping_ratio: Optional[float] = Field(default=None, description="Approved project report benchmark stripping ratio")


@tool(args_schema=ProductionInput)
def analyze_production_grid(file_path: str, benchmark_stripping_ratio: Optional[float] = None) -> dict:
    """Ingests and analyzes tabular monthly coal production and overburden excavation spreadsheets."""
    logger.info(f"Executing tool: analyze_production_grid on {file_path}")
    try:
        analyzer = ProductionGridAnalyzer(benchmark_stripping_ratio=benchmark_stripping_ratio)
        return analyzer.analyze(file_path).model_dump()
    except Exception as e:
        logger.error(f"Error in analyze_production_grid: {e}")
        return {"status": "ERROR", "error": str(e)}


# Backward-compatible tool alias for thickness grid callers
@tool
def analyze_thickness_grid(file_path: str, **kwargs) -> dict:
    """Compatibility alias: maps thickness matrix requests to production grid analysis."""
    return analyze_production_grid.invoke({"file_path": file_path})
