import hashlib
import json
import datetime
import sqlite3
import uuid
import os
import stat
import hmac
import secrets
import sys

class AuditLedger:
    """
    A persistent cryptographic audit ledger for local AI applications.
    Uses SQLite for concurrent-safe append-only storage.
    Uses HMAC-SHA256 to provide integrity/authentication of events under a shared secret.
    (Note: HMAC proves the local system generated this event, but does not provide
    asymmetric per-agent identity).
    """
    def __init__(self, db_path="data/audit/audit_ledger.db", secret_key_path="data/audit/ledger_secret.key"):
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        self.db_path = os.path.join(workspace_root, db_path)
        self.secret_key_path = os.path.join(workspace_root, secret_key_path)
        
        # Ensure the storage directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(os.path.dirname(self.secret_key_path), exist_ok=True)

        
        # Load or generate the HMAC secret key
        if os.path.exists(self.secret_key_path):
            with open(self.secret_key_path, "rb") as f:
                self.secret_key = f.read()
        else:
            self.secret_key = secrets.token_bytes(32)
            with open(self.secret_key_path, "wb") as f:
                f.write(self.secret_key)
            # Attempt to restrict file permissions to the current user
            try:
                os.chmod(self.secret_key_path, stat.S_IREAD | stat.S_IWRITE)
            except Exception:
                pass
                    
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Enable Write-Ahead Logging for better concurrency
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS audit_chain (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_uuid TEXT UNIQUE,
                    timestamp TEXT,
                    event_type TEXT,
                    workflow_id TEXT,
                    tool_name TEXT,
                    caller TEXT,
                    agent_version TEXT,
                    tool_version TEXT,
                    inputs_json TEXT,
                    outputs_json TEXT,
                    status TEXT,
                    signature TEXT,
                    previous_hash TEXT,
                    block_hash TEXT
                )
            """)
            
            cursor.execute("SELECT COUNT(*) FROM audit_chain")
            if cursor.fetchone()[0] == 0:
                self._create_genesis_block(cursor)
            conn.commit()

    def _create_genesis_block(self, cursor):
        genesis_uuid = str(uuid.uuid4())
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        
        genesis_data = {
            "event_uuid": genesis_uuid,
            "timestamp": timestamp,
            "event_type": "SYSTEM_EVENT",
            "workflow_id": "INIT",
            "tool_name": "system_init",
            "caller": "system_admin",
            "agent_version": "1.0.0",
            "tool_version": "1.0.0",
            "inputs_json": "{}",
            "outputs_json": "{}",
            "status": "INITIALIZED",
            "previous_hash": "0" * 64
        }
        
        signature = self._sign_payload(genesis_data)
        genesis_data["signature"] = signature
        block_hash = self._calculate_block_hash(genesis_data)
        
        cursor.execute("""
            INSERT INTO audit_chain 
            (event_uuid, timestamp, event_type, workflow_id, tool_name, caller, 
            agent_version, tool_version, inputs_json, outputs_json, status, 
            signature, previous_hash, block_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            genesis_data["event_uuid"], genesis_data["timestamp"], 
            genesis_data["event_type"], genesis_data["workflow_id"],
            genesis_data["tool_name"], genesis_data["caller"],
            genesis_data["agent_version"], genesis_data["tool_version"],
            genesis_data["inputs_json"], genesis_data["outputs_json"], 
            genesis_data["status"], genesis_data["signature"], 
            genesis_data["previous_hash"], block_hash
        ))

    def _sign_payload(self, data_dict):
        canonical_string = json.dumps(data_dict, sort_keys=True).encode('utf-8')
        return hmac.new(self.secret_key, canonical_string, hashlib.sha256).hexdigest()

    def _calculate_block_hash(self, block_dict):
        canonical_string = json.dumps(block_dict, sort_keys=True).encode('utf-8')
        return hashlib.sha256(canonical_string).hexdigest()

    @staticmethod
    def hash_artifact(file_path):
        """Utility to calculate SHA-256 of external files to store in inputs_json"""
        sha256 = hashlib.sha256()
        try:
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except FileNotFoundError:
            return None

    def append_event(self, event_type, workflow_id, tool_name, caller, 
                     agent_version, tool_version, inputs, outputs, status):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Exclusive lock to serialize appends
            cursor.execute("BEGIN EXCLUSIVE")
            
            cursor.execute("SELECT block_hash FROM audit_chain ORDER BY id DESC LIMIT 1")
            previous_hash = cursor.fetchone()[0]
            
            event_uuid = str(uuid.uuid4())
            timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
            inputs_json = json.dumps(inputs, sort_keys=True)
            outputs_json = json.dumps(outputs, sort_keys=True)
            
            payload = {
                "event_uuid": event_uuid,
                "timestamp": timestamp,
                "event_type": event_type,
                "workflow_id": workflow_id,
                "tool_name": tool_name,
                "caller": caller,
                "agent_version": agent_version,
                "tool_version": tool_version,
                "inputs_json": inputs_json,
                "outputs_json": outputs_json,
                "status": status,
                "previous_hash": previous_hash
            }
            
            signature = self._sign_payload(payload)
            payload["signature"] = signature
            block_hash = self._calculate_block_hash(payload)
            
            cursor.execute("""
                INSERT INTO audit_chain 
                (event_uuid, timestamp, event_type, workflow_id, tool_name, caller, 
                agent_version, tool_version, inputs_json, outputs_json, status, 
                signature, previous_hash, block_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                event_uuid, timestamp, event_type, workflow_id, tool_name, caller, 
                agent_version, tool_version, inputs_json, outputs_json, status, 
                signature, previous_hash, block_hash
            ))
            conn.commit()
            return block_hash

    def verify_integrity(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_chain ORDER BY id ASC")
            rows = cursor.fetchall()
            col_names = [description[0] for description in cursor.description]
            
            if not rows:
                print("⚠️ Ledger is empty.")
                return False
                
            previous_block_hash = "0" * 64
            
            for i, row in enumerate(rows):
                row_dict = dict(zip(col_names, row))
                
                # 1. Verify Hash Chain Link
                if i == 0:
                    if row_dict["previous_hash"] != "0" * 64:
                        print(f"❌ Genesis block corrupted! Invalid previous_hash.")
                        return False
                else:
                    if row_dict["previous_hash"] != previous_block_hash:
                        print(f"❌ Link broken at Block ID {row_dict['id']}! (Deletion, Insertion, or Reordering detected)")
                        return False
                
                # 2. Reconstruct payload
                payload = {
                    "event_uuid": row_dict["event_uuid"],
                    "timestamp": row_dict["timestamp"],
                    "event_type": row_dict["event_type"],
                    "workflow_id": row_dict["workflow_id"],
                    "tool_name": row_dict["tool_name"],
                    "caller": row_dict["caller"],
                    "agent_version": row_dict["agent_version"],
                    "tool_version": row_dict["tool_version"],
                    "inputs_json": row_dict["inputs_json"],
                    "outputs_json": row_dict["outputs_json"],
                    "status": row_dict["status"],
                    "previous_hash": row_dict["previous_hash"]
                }
                
                # Verify HMAC Signature (Provenance against database modification)
                expected_sig = self._sign_payload(payload)
                if not hmac.compare_digest(expected_sig, row_dict["signature"]):
                    print(f"❌ HMAC Signature mismatch at Block ID {row_dict['id']}! Payload was modified.")
                    return False
                
                # Verify Block Hash
                payload["signature"] = row_dict["signature"]
                expected_block_hash = self._calculate_block_hash(payload)
                if expected_block_hash != row_dict["block_hash"]:
                    print(f"❌ Block Hash mismatch at Block ID {row_dict['id']}! Row was modified.")
                    return False
                    
                previous_block_hash = row_dict["block_hash"]
                
        print(f"[OK] Audit ledger integrity verified! {len(rows)} blocks cryptographically validated.")
        return True


    def get_latest_events(self, limit=50):
        """Fetches the latest audit events from SQLite as dictionaries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, timestamp, workflow_id, tool_name, caller, status, block_hash FROM audit_chain ORDER BY id DESC LIMIT ?", (int(limit),))
            rows = cursor.fetchall()
            col_names = [d[0] for d in cursor.description]
            return [dict(zip(col_names, row)) for row in rows]


from langchain_core.tools import tool
from pydantic import BaseModel, Field
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


@tool
def write_sha256_audit_seal(file_path: str) -> str:
    """Calculates and writes a SHA256 audit seal for the artifact."""
    print(f"\n--- EXECUTING TOOL: write_sha256_audit_seal ---\n")
    logger.info(f"Executing tool: write_sha256_audit_seal")
    try:
        return AuditLedger.hash_artifact(file_path)
    except Exception as e:
        logger.error(f"Error in write_sha256_audit_seal: {e}")
        return str(e)

