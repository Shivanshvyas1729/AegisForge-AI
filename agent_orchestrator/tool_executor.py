"""
AegisForge-AI — Tool Execution Dispatcher
==========================================
Handles the case where smaller local LLMs emit tool calls as JSON text
instead of native function calls. Parses the JSON and dispatches to the
correct tool implementation.

Fixes:
  #7  — _parse_text_tool_call now uses json.JSONDecoder.raw_decode (handles
         nested JSON correctly, strips markdown fences).
  #11 — Docker sandbox has a subprocess fallback when Docker is unavailable.
"""

import re
import json
import logging
import subprocess
import tempfile
import os
from typing import Tuple

from agent_orchestrator.models import LANGFUSE_CONFIG

logger = logging.getLogger("AegisForge.ToolExecutor")


# ============================================================================
# JSON TOOL CALL PARSER  (Fix #7 — handles nested JSON + markdown fences)
# ============================================================================

def parse_text_tool_call(content: str) -> Tuple[str, dict]:
    """
    Parse a JSON tool call emitted as plain text by the LLM.

    Improvements over the old regex approach:
    - Uses json.JSONDecoder.raw_decode to handle any nesting depth.
    - Strips markdown code fences before parsing.
    - Returns (tool_name, args) or ("", {}) if not found.
    """
    # Strip markdown code fences
    cleaned = re.sub(r'```(?:json)?\s*', '', content).strip()

    decoder = json.JSONDecoder()
    idx = 0
    while idx < len(cleaned):
        start = cleaned.find('{', idx)
        if start == -1:
            break
        try:
            obj, _ = decoder.raw_decode(cleaned, start)
            if isinstance(obj, dict) and obj.get("name"):
                name = str(obj["name"])
                args = obj.get("arguments",
                        obj.get("parameters",
                        obj.get("args", {})))
                if not isinstance(args, dict):
                    args = {}
                return name, args
        except json.JSONDecodeError:
            pass
        idx = start + 1

    return "", {}


# ============================================================================
# CODER TOOL DISPATCHER  (Fix #11 — Docker fallback to subprocess)
# ============================================================================

def _run_in_subprocess(code: str, title: str = "") -> str:
    """Fallback: run code in a local subprocess when Docker is unavailable."""
    logger.warning("Docker unavailable — running code in restricted local subprocess")
    try:
        with tempfile.NamedTemporaryFile(
            mode='w', suffix='.py', delete=False, encoding='utf-8'
        ) as f:
            f.write(code)
            fname = f.name

        result = subprocess.run(
            ["python", fname],
            capture_output=True, text=True, timeout=30,
            env={k: v for k, v in os.environ.items()
                 if k not in ("PYTHONPATH",)}   # isolate env
        )
        output = result.stdout or result.stderr or "(no output)"
        status = "COMPLETED" if result.returncode == 0 else f"FAILED (exit {result.returncode})"
        return f"[SUBPROCESS_OUTPUT (no Docker)]:\n{output}\n[STATUS: {status}]"
    except subprocess.TimeoutExpired:
        return "[TOOL_ERROR]: Subprocess timed out after 30 seconds"
    except Exception as e:
        return f"[TOOL_ERROR]: Subprocess execution failed: {e}"
    finally:
        try:
            os.unlink(fname)
        except Exception:
            pass


def _clean_tool_args(args: dict) -> dict:
    """Sanitize arguments parsed from LLM JSON calls."""
    if not isinstance(args, dict):
        return {}
    cleaned = dict(args)
    if "kwargs" in cleaned:
        kw = cleaned["kwargs"]
        if isinstance(kw, str):
            try:
                parsed = json.loads(kw)
                cleaned["kwargs"] = parsed if isinstance(parsed, dict) else None
            except Exception:
                cleaned.pop("kwargs", None)
    # Convert string booleans to actual booleans
    bool_keys = ["is_single_source", "has_pac", "is_emergency", "vendor_is_blacklisted"]
    for k in bool_keys:
        if k in cleaned and isinstance(cleaned[k], str):
            cleaned[k] = cleaned[k].strip().lower() in ("true", "1", "yes", "y", "t")
    return cleaned


def execute_coder_tool(tool_name: str, args: dict, all_context: str = "") -> str:
    """
    Execute a coder tool by name with given args.
    Falls back to subprocess if Docker is unavailable.
    """
    from tools import (
        asme_calculator,
        api_579_ffs_tool,
        material_lookup_tool,
        docker_sandbox,
    )

    args = _clean_tool_args(args)
    name_lower = tool_name.lower()

    try:
        # --- execute_in_sandbox ---
        if any(kw in name_lower for kw in ["sandbox", "execute", "run_code"]):
            code = (args.get("code_string") or args.get("code") or
                    args.get("code_str", ""))
            title = (args.get("task_title") or args.get("title") or
                     "Sandbox Execution")
            if not code:
                return "[ERROR]: No code_string found in tool arguments"
            try:
                res = docker_sandbox.execute_in_sandbox.invoke(
                    {"code_string": code, "task_title": title},
                    config=LANGFUSE_CONFIG
                )
                output = res.get("output", res.get("stdout", str(res)))
                status = res.get("status", "COMPLETED")
                return f"[DOCKER_SANDBOX_OUTPUT]:\n{output}\n[STATUS: {status}]"
            except Exception as docker_err:
                logger.warning(f"Docker unavailable ({docker_err}), using subprocess fallback")
                return _run_in_subprocess(code, title)

        # --- calculate_asme_stresses ---
        elif any(kw in name_lower for kw in ["asme", "calculate_asme", "stress"]):
            if all_context:
                if not args.get("design_pressure_mpa"):
                    p_m = re.search(r'(?:design\s+pressure|pressure|\$P|P)[:\s=]*([\d.]+)', all_context, re.I)
                    if p_m: args["design_pressure_mpa"] = float(p_m.group(1))
                if not args.get("inside_radius_mm"):
                    r_m = re.search(r'(?:inside\s+radius|radius|\$R|R)[:\s=]*([\d.]+)', all_context, re.I)
                    if r_m: args["inside_radius_mm"] = float(r_m.group(1))
                if not args.get("allowable_stress_mpa"):
                    s_m = re.search(r'(?:allowable\s+stress|stress|\$S|S)[:\s=]*([\d.]+)', all_context, re.I)
                    if s_m: args["allowable_stress_mpa"] = float(s_m.group(1))
                if not args.get("corrosion_allowance_mm"):
                    ca_m = re.search(r'(?:corrosion\s+allowance|\$CA|CA)[:\s=]*([\d.]+)', all_context, re.I)
                    if ca_m: args["corrosion_allowance_mm"] = float(ca_m.group(1))
                if not args.get("measured_thickness_mm"):
                    t_m = re.search(r'(?:actual\s+thickness|measured\s+thickness|t_actual|t_meas)[:\s=]*([\d.]+)', all_context, re.I)
                    if t_m: args["measured_thickness_mm"] = float(t_m.group(1))
                if not args.get("corrosion_rate_mm_yr"):
                    cr_m = re.search(r'(?:corrosion\s+rate|\$CR|CR)[:\s=]*([\d.]+)', all_context, re.I)
                    if cr_m: args["corrosion_rate_mm_yr"] = float(cr_m.group(1))
            res = asme_calculator.calculate_asme_stresses.invoke(args, config=LANGFUSE_CONFIG)
            return f"[CALCULATION_RESULT]:\n{json.dumps(res, indent=2, default=str)}"

        # --- lookup_material ---
        elif any(kw in name_lower for kw in ["material", "lookup"]):
            res = material_lookup_tool.lookup_material.invoke(args, config=LANGFUSE_CONFIG)
            return f"[MATERIAL_LOOKUP_RESULT]:\n{res}"

        # --- run_ffs_assessment ---
        elif any(kw in name_lower for kw in ["ffs", "fitness"]):
            res = api_579_ffs_tool.run_ffs_assessment.invoke(args, config=LANGFUSE_CONFIG)
            return f"[FFS_RESULT]:\n{res}"

    except Exception as e:
        logger.error(f"Coder tool execution error for '{tool_name}': {e}")
        return f"[TOOL_ERROR]: {e}"

    return f"[UNKNOWN_TOOL]: {tool_name}"


# ============================================================================
# REASONING TOOL DISPATCHER
# ============================================================================

def execute_reasoning_tool(tool_name: str, args: dict, all_context: str = "") -> str:
    """Execute a reasoning/compliance tool by name."""
    from tools import (
        compliance_auditor,
        risk_based_inspection_tool,
        routing_guard,
    )

    args = _clean_tool_args(args)
    name_lower = tool_name.lower()
    try:
        if any(kw in name_lower for kw in ["cvc", "compliance", "audit", "procurement"]):
            if not args.get("equipment_id") and all_context:
                m_eq = re.search(
                    r'\b(\d{1,3}-[A-Z]{1,3}-\d{2,4}|pump\s+[A-Z0-9-]+|vessel\s+[A-Z0-9-]+)',
                    all_context, re.I
                )
                if m_eq:
                    args["equipment_id"] = m_eq.group(0).strip()
            if not args.get("estimated_cost_lakhs") and all_context:
                m_cost = re.search(r'([\d.]+)\s*(?:lakhs?|lakh)', all_context, re.I)
                if m_cost:
                    args["estimated_cost_lakhs"] = float(m_cost.group(1))
            if not args.get("applicable_cvc_clause") and all_context:
                m_clause = re.search(
                    r'(GFR[\s\w/.,]+Rule\s*\d+|CVC[^.\n]{0,60}|Rule\s*\d+[^.\n]{0,40})',
                    all_context, re.I
                )
                if m_clause:
                    args["applicable_cvc_clause"] = m_clause.group(0).strip()
            res = compliance_auditor.audit_cvc_compliance.invoke(args, config=LANGFUSE_CONFIG)
            return f"[COMPLIANCE_RESULT]:\n{json.dumps(res, indent=2, default=str)}"

        elif any(kw in name_lower for kw in ["rbi", "risk"]):
            res = risk_based_inspection_tool.calculate_rbi_score.invoke(args, config=LANGFUSE_CONFIG)
            return f"[RBI_RESULT]:\n{res}"

        elif "routing" in name_lower or "verify" in name_lower:
            res = routing_guard.verify_routing_policy.invoke(args, config=LANGFUSE_CONFIG)
            return f"[ROUTING_RESULT]:\n{res}"

        elif any(kw in name_lower for kw in ["knowledge", "search", "rag", "sop", "circular", "rule", "statutory_audit"]):
            from tools import rag
            query = args.get("query") or args.get("search_query") or args.get("question") or all_context[:200]
            top_k = int(args.get("top_k", 3))
            res = rag.search_local_knowledge.invoke({"query": query, "top_k": top_k}, config=LANGFUSE_CONFIG)
            return f"[KNOWLEDGE_SEARCH_RESULT]:\n{res}"

    except Exception as e:
        logger.error(f"Reasoning tool error for '{tool_name}': {e}")
        return f"[TOOL_ERROR]: {e}"

    return f"[UNKNOWN_TOOL]: {tool_name}"


# ============================================================================
# VISION TOOL DISPATCHER
# ============================================================================

def execute_vision_tool(tool_name: str, args: dict) -> str:
    """Execute a vision tool by name."""
    from tools import (
        inspection_extractor_tool,
        thickness_grid_analyzer,
        file_io,
    )

    name_lower = tool_name.lower()
    try:
        if any(kw in name_lower for kw in ["extract", "inspection"]):
            res = inspection_extractor_tool.extract_inspection_data.invoke(args, config=LANGFUSE_CONFIG)
            return f"[EXTRACTION_RESULT]:\n{res}"
        elif any(kw in name_lower for kw in ["thickness", "grid", "analyze"]):
            res = thickness_grid_analyzer.analyze_thickness_grid.invoke(args, config=LANGFUSE_CONFIG)
            return f"[GRID_ANALYSIS_RESULT]:\n{res}"
        elif any(kw in name_lower for kw in ["pdf", "read", "scanned"]):
            res = file_io.read_scanned_pdf.invoke(args, config=LANGFUSE_CONFIG)
            return f"[PDF_CONTENT]:\n{str(res)[:2000]}"
    except Exception as e:
        logger.error(f"Vision tool error for '{tool_name}': {e}")
        return f"[TOOL_ERROR]: {e}"
    return f"[UNKNOWN_TOOL]: {tool_name}"
