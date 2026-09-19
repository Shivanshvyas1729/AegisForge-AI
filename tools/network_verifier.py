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
        pid = psutil.Process().pid
        # Scan all active inet connections belonging to this process
        connections = psutil.Process(pid).connections(kind='inet')
        
        external_conns = []
        local_conns = []
        
        for conn in connections:
            if conn.status == 'ESTABLISHED':
                remote_ip = conn.raddr.ip if conn.raddr else None
                if remote_ip:
                    if remote_ip in self.allowed_ips or remote_ip.startswith("127."):
                        local_conns.append(f"{conn.laddr.ip}:{conn.laddr.port} -> {remote_ip}:{conn.raddr.port}")
                    else:
                        external_conns.append(f"EXTERNAL EGRESS DETECTED: {conn.laddr.ip}:{conn.laddr.port} -> {remote_ip}:{conn.raddr.port}")
        
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
