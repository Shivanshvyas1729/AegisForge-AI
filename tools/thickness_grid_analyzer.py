import sys
import os
import csv
import statistics
from typing import Optional, List, Dict

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.vision import ThicknessGridResult
from tools.audit_trail import AuditLedger

try:
    import openpyxl
except ImportError:
    openpyxl = None


class ThicknessGridAnalyzer:
    """
    Ultrasonic Thickness (UT) matrix analyzer for industrial inspection grids.

    Ingests N x M coordinate thickness grids from .xlsx or .csv files,
    calculates statistical wall degradation, detects outlier pits, and
    identifies localized thinning coordinates across the vessel circumference.
    """

    def __init__(self, nominal_thickness_mm: Optional[float] = None, use_audit_trail: bool = True):
        self.nominal_thickness = nominal_thickness_mm
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def _read_csv(self, file_path: str) -> list:
        """Read thickness grid from CSV file. Returns flat list of float values."""
        values = []
        with open(file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.reader(f)
            for row_idx, row in enumerate(reader):
                for col_idx, cell in enumerate(row):
                    cell = cell.strip()
                    if cell:
                        try:
                            val = float(cell)
                            values.append({"row": row_idx + 1, "col": col_idx + 1, "thickness": val})
                        except ValueError:
                            continue  # Skip header cells or non-numeric data
        return values

    def _read_xlsx(self, file_path: str) -> list:
        """Read thickness grid from Excel file. Returns flat list of float values."""
        if openpyxl is None:
            raise RuntimeError("openpyxl is required for .xlsx processing. Install: pip install openpyxl")

        values = []
        wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
        ws = wb.active
        for row_idx, row in enumerate(ws.iter_rows(values_only=True), start=1):
            for col_idx, cell in enumerate(row, start=1):
                if cell is not None:
                    try:
                        val = float(cell)
                        values.append({"row": row_idx, "col": col_idx, "thickness": val})
                    except (ValueError, TypeError):
                        continue
        wb.close()
        return values

    def _detect_outliers(self, data_points: list, threshold_factor: float = 2.0) -> list:
        """Detect outlier pits using IQR method."""
        thicknesses = [p["thickness"] for p in data_points]
        if len(thicknesses) < 4:
            return []

        sorted_t = sorted(thicknesses)
        n = len(sorted_t)
        q1 = sorted_t[n // 4]
        q3 = sorted_t[3 * n // 4]
        iqr = q3 - q1
        lower_bound = q1 - threshold_factor * iqr

        nom = self.nominal_thickness or max(thicknesses)
        outliers = []
        for point in data_points:
            if point["thickness"] < lower_bound:
                outliers.append({
                    "row": point["row"],
                    "col": point["col"],
                    "thickness_mm": point["thickness"],
                    "deviation_from_nominal_mm": round(nom - point["thickness"], 2)
                })
        return outliers

    def analyze(self, file_path: str, caller_agent: str = "vision_agent") -> ThicknessGridResult:
        """
        Main entry point. Analyzes a UT thickness grid file and returns
        statistical analysis with critical coordinate identification.
        """
        if not os.path.exists(file_path):
            result = ThicknessGridResult(status="ERROR", error=f"File not found: {file_path}")
            return self._log_and_return(result, file_path, caller_agent, "FAILED")

        ext = os.path.splitext(file_path)[1].lower()

        try:
            if ext == '.csv':
                data_points = self._read_csv(file_path)
            elif ext in ['.xlsx', '.xls']:
                data_points = self._read_xlsx(file_path)
            else:
                result = ThicknessGridResult(status="ERROR", error=f"Unsupported file type: {ext}. Use .csv or .xlsx")
                return self._log_and_return(result, file_path, caller_agent, "FAILED")
        except Exception as e:
            result = ThicknessGridResult(status="ERROR", error=f"Failed to read file: {e}")
            return self._log_and_return(result, file_path, caller_agent, "FAILED")

        if not data_points:
            result = ThicknessGridResult(status="ERROR", error="No numeric thickness data found in grid.")
            return self._log_and_return(result, file_path, caller_agent, "FAILED")

        thicknesses = [p["thickness"] for p in data_points]
        min_val = min(thicknesses)
        max_val = max(thicknesses)
        mean_val = statistics.mean(thicknesses)

        # Find the critical (minimum) coordinate
        min_point = min(data_points, key=lambda p: p["thickness"])
        critical_coord = f"Row {min_point['row']}, Col {min_point['col']}"

        # Determine nominal thickness dynamically if not explicitly specified
        nom_t = self.nominal_thickness
        if nom_t is None or nom_t <= 0:
            nom_t = round(max_val)  # Unworn plate thickness estimate
        self.nominal_thickness = nom_t

        # Wall loss percentage relative to nominal
        mean_loss_pct = round(((nom_t - mean_val) / nom_t) * 100, 2) if nom_t > 0 else 0.0

        # Detect outlier pits
        outliers = self._detect_outliers(data_points)

        # Estimate flaw length from adjacent thin points (simplified: count points below nominal - 2mm)
        thin_threshold = nom_t - 2.0
        thin_points = [p for p in data_points if p["thickness"] < thin_threshold]
        flaw_length = len(thin_points) * 25.0  # Approximate 25mm grid spacing

        result = ThicknessGridResult(
            status="SUCCESS",
            grid_points_scanned=len(data_points),
            nominal_thickness_mm=nom_t,
            min_point_thickness_mm=round(min_val, 2),
            max_point_thickness_mm=round(max_val, 2),
            mean_thickness_mm=round(mean_val, 2),
            critical_coordinate=critical_coord,
            mean_loss_percentage=mean_loss_pct,
            flaw_length_mm=round(flaw_length, 2),
            outlier_points=outliers
        )
        return self._log_and_return(result, file_path, caller_agent, "COMPLETED")

    def _log_and_return(self, result: ThicknessGridResult, file_path: str, caller_agent: str, status: str) -> ThicknessGridResult:
        if self.use_audit_trail:
            file_hash = AuditLedger.hash_artifact(file_path) or "FILE_NOT_FOUND"
            self.ledger.append_event(
                event_type="DATA_EXTRACTION",
                workflow_id="UT_GRID_ANALYSIS",
                tool_name="thickness_grid_analyzer",
                caller=caller_agent,
                agent_version="1.0.0",
                tool_version="1.0.0",
                inputs={"file_path": file_path, "file_hash": file_hash, "nominal_thickness_mm": self.nominal_thickness},
                outputs=result.model_dump(),
                status=status
            )
        return result

from langchain_core.tools import tool
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@tool
def analyze_thickness_grid(file_path: str, nominal_thickness_mm: Optional[float] = None) -> dict:
    """Analyzes a thickness grid CSV or Excel file for localized thinning."""
    print(f"\n--- EXECUTING TOOL: analyze_thickness_grid ---\n")
    logger.info(f"Executing tool: analyze_thickness_grid (File: {file_path})")
    try:
        analyzer = ThicknessGridAnalyzer(nominal_thickness_mm=nominal_thickness_mm)
        return analyzer.analyze(file_path).model_dump()
    except Exception as e:
        logger.error(f"Error in analyze_thickness_grid: {e}")
        return {"status": "error", "error": str(e)}
