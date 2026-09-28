import sys
import os
import psutil
import datetime

# Ensure the root workspace is in the python path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.network import NetworkTelemetryReport
from tools.audit_trail import AuditLedger

class NetworkVerifier:
    def __init__(self, use_audit_trail: bool = True):
        # The ONLY allowed connections for a completely offline AI are local loopbacks 
        # (e.g., talking to the local Ollama LLM server on the same machine).
        self.allowed_ips = ["127.0.0.1", "::1", "localhost", "0.0.0.0"]
        
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def verify_zero_egress(self) -> NetworkTelemetryReport:
        """
        Checks ALL system-level inet connections (not just this process) for
        external egress. This catches Docker, Ollama, and Streamlit subprocess
        connections that psutil.Process(pid) would miss. (Fix #20)
        """
        pid = psutil.Process().pid

        # Use net_connections for system-wide check (Fix #20)
        try:
            all_connections = psutil.net_connections(kind='inet')
        except (psutil.AccessDenied, AttributeError):
            # Fallback to per-process check if system-wide is denied (non-admin)
            all_connections = psutil.Process(pid).connections(kind='inet')

        external_conns = []
        local_conns = []

        for conn in all_connections:
            if conn.status == 'ESTABLISHED' and conn.raddr:
                remote_ip = conn.raddr.ip
                if remote_ip in self.allowed_ips or remote_ip.startswith("127."):
                    local_conns.append(
                        f"{conn.laddr.ip}:{conn.laddr.port} -> {remote_ip}:{conn.raddr.port}"
                    )
                else:
                    external_conns.append(
                        f"EXTERNAL EGRESS DETECTED: {conn.laddr.ip}:{conn.laddr.port} "
                        f"-> {remote_ip}:{conn.raddr.port}"
                    )

        is_air_gapped = len(external_conns) == 0

        if is_air_gapped:
            status = "SECURE: Zero Egress Detected. Sovereign Air-Gap Verified."
        else:
            status = "CRITICAL BREACH: Unauthorized external data exfiltration detected!"

        report = NetworkTelemetryReport(
            timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat(),
            process_id=pid,
            is_air_gapped=is_air_gapped,
            external_connections=external_conns,
            local_connections=local_conns,
            verification_status=status
        )

        # Mandated by architecture.md: Cryptographically audit every security check
        if self.use_audit_trail:
            ledger_status = "APPROVED" if is_air_gapped else "BLOCKED_BY_SECURITY"
            self.ledger.append_event(
                event_type="NETWORK_SECURITY_CHECK",
                workflow_id="AIR_GAP_VERIFICATION",
                tool_name="network_verifier",
                caller="system_monitor",
                agent_version="1.0.0",
                tool_version="1.0.0",
                inputs={"pid": pid, "allowed_ips": self.allowed_ips},
                outputs=report.model_dump(),
                status=ledger_status
            )
            
        return report

from langchain_core.tools import tool
from pydantic import BaseModel
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class VerifyInput(BaseModel):
    pass

@tool
def verify_zero_egress() -> dict:
    """Verifies zero external egress telemetry from the environment."""
    print(f"\n--- EXECUTING TOOL: verify_zero_egress ---\n")
    logger.info(f"Executing tool: verify_zero_egress")
    try:
        verifier = NetworkVerifier()
        return verifier.verify_zero_egress().model_dump()
    except Exception as e:
        logger.error(f"Error in verify_zero_egress: {e}")
        return {"status": "error", "error": str(e)}
