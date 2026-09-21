"""
Cryptographic Forensic Ledger & Tamper-Proof Audit Service
==========================================================
Queries immutable SQLite audit records, verifies SHA-256 seals, and validates block hash chains.
"""

import sqlite3
import hashlib
from typing import List, Dict, Any, Optional
from pathlib import Path
from tools.audit_trail import AuditLedger


class AuditService:
    """Service providing non-repudiation and cryptographic audit trail verification."""

    def __init__(self, ledger: Optional[AuditLedger] = None):
        self.ledger = ledger or AuditLedger()

    def get_latest_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Retrieves the most recent audit events from the SQLite cryptographic chain.
        """
        try:
            with sqlite3.connect(self.ledger.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, event_uuid, timestamp, event_type, workflow_id, tool_name, caller, status, block_hash "
                    "FROM audit_chain ORDER BY id DESC LIMIT ?",
                    (int(limit),)
                )
                rows = cursor.fetchall()
                col_names = [d[0] for d in cursor.description]
                return [dict(zip(col_names, row)) for row in rows]
        except Exception as e:
            return [{"id": 0, "error": f"Failed to read ledger: {e}", "status": "ERROR"}]

    def verify_ledger_integrity(self) -> bool:
        """
        Cryptographically verifies the HMAC signatures and block hash chain from Genesis.
        """
        try:
            return self.ledger.verify_integrity()
        except Exception:
            return False

    def hash_artifact(self, file_path: str) -> Optional[str]:
        """
        Computes the cryptographic SHA-256 hash of a file on disk.
        """
        return AuditLedger.hash_artifact(file_path)

    def verify_document_hash(self, file_path: str, expected_hash: str) -> bool:
        """
        Validates whether a document's current SHA-256 matches its registered cryptographic seal.
        """
        actual_hash = self.hash_artifact(file_path)
        if not actual_hash or not expected_hash:
            return False
        return actual_hash.lower() == expected_hash.lower()
