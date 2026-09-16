"""
tools/audit_trail.py
Cryptographically Hash-Chained Sovereign Audit Ledger.
Provides tamper-evident, append-only logging for all agent tool executions,
ASME calculations, compliance audits, and system security events.
"""

import os
import sys
import json
import hashlib
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, Tuple, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_LEDGER_PATH = PROJECT_ROOT / "data" / "logs" / "sovereign_audit_ledger.jsonl"
GENESIS_HASH = "0" * 64

_ledger_lock = threading.Lock()


def _canonical_json(data: Dict[str, Any]) -> str:
    """Produces deterministic canonical JSON string without whitespace variations."""
    return json.dumps(data, sort_keys=True, separators=(',', ':'), ensure_ascii=True, default=str)


def get_latest_entry_hash(ledger_path: Optional[Path] = None) -> str:
    """Reads the last valid entry hash from the ledger file, or returns GENESIS_HASH."""
    path = ledger_path or DEFAULT_LEDGER_PATH
    if not path.exists() or path.stat().st_size == 0:
        return GENESIS_HASH

    last_line = ""
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                last_line = line_str

    if not last_line:
        return GENESIS_HASH

    try:
        data = json.loads(last_line)
        return data.get("entry_hash", GENESIS_HASH)
    except Exception:
        return GENESIS_HASH


def append_audit_event(
    tool_name: str,
    inputs: Dict[str, Any],
    outputs: Dict[str, Any],
    status: str = "SUCCESS",
    duration_ms: float = 0.0,
    caller: str = "agent",
    ledger_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Appends a new cryptographically chained audit record to sovereign_audit_ledger.jsonl.
    Hash chain: entry_hash = SHA256(prev_entry_hash + canonical_json(payload))
    """
    path = ledger_path or DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)

    with _ledger_lock:
        prev_hash = get_latest_entry_hash(path)
        timestamp_utc = datetime.now(timezone.utc).isoformat()

        # Sanitize / summarize inputs to prevent logging huge binary payloads
        safe_inputs = {}
        for k, v in inputs.items():
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                str_v = str(v)
                safe_inputs[k] = str_v if len(str_v) <= 1000 else str_v[:997] + "..."
            else:
                safe_inputs[k] = type(v).__name__

        safe_outputs = {}
        for k, v in outputs.items():
            if isinstance(v, (str, int, float, bool, list, dict)) or v is None:
                str_v = str(v)
                safe_outputs[k] = str_v if len(str_v) <= 1000 else str_v[:997] + "..."
            else:
                safe_outputs[k] = type(v).__name__

        payload = {
            "timestamp_utc": timestamp_utc,
            "tool_name": tool_name,
            "caller": caller,
            "status": status,
            "duration_ms": round(duration_ms, 2),
            "inputs": safe_inputs,
            "outputs": safe_outputs,
        }

        # Cryptographic link to previous record
        to_hash = prev_hash + _canonical_json(payload)
        entry_hash = hashlib.sha256(to_hash.encode("utf-8")).hexdigest()

        record = {
            "prev_entry_hash": prev_hash,
            "entry_hash": entry_hash,
            **payload
        }

        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=True) + "\n")

        return record


def verify_audit_ledger_integrity(ledger_path: Optional[Path] = None) -> Tuple[bool, str, int]:
    """
    Verifies the entire cryptographic hash chain of the ledger from genesis to head.
    Returns:
        (is_valid: bool, status_message: str, verified_count: int)
    """
    path = ledger_path or DEFAULT_LEDGER_PATH
    if not path.exists():
        return True, "Ledger is empty (no file).", 0

    count = 0
    expected_prev_hash = GENESIS_HASH

    with _ledger_lock:
        with open(path, "r", encoding="utf-8") as f:
            for idx, line in enumerate(f, start=1):
                line_str = line.strip()
                if not line_str:
                    continue

                try:
                    record = json.loads(line_str)
                except Exception as e:
                    return False, f"JSON parse error at line {idx}: {e}", count

                prev_hash = record.get("prev_entry_hash")
                claimed_hash = record.get("entry_hash")

                if prev_hash != expected_prev_hash:
                    return (
                        False,
                        f"Hash chain broken at entry {idx}! Expected prev_hash '{expected_prev_hash[:16]}...', got '{prev_hash[:16] if prev_hash else None}...'",
                        count
                    )

                # Recompute payload hash
                payload = {
                    "timestamp_utc": record.get("timestamp_utc"),
                    "tool_name": record.get("tool_name"),
                    "caller": record.get("caller"),
                    "status": record.get("status"),
                    "duration_ms": record.get("duration_ms"),
                    "inputs": record.get("inputs"),
                    "outputs": record.get("outputs"),
                }
                to_hash = expected_prev_hash + _canonical_json(payload)
                computed_hash = hashlib.sha256(to_hash.encode("utf-8")).hexdigest()

                if computed_hash != claimed_hash:
                    return (
                        False,
                        f"Tamper detected at entry {idx}! Claimed hash '{claimed_hash[:16]}...' does not match computed hash '{computed_hash[:16]}...'",
                        count
                    )

                expected_prev_hash = claimed_hash
                count += 1

    return True, f"Cryptographic integrity verified across {count} records.", count
