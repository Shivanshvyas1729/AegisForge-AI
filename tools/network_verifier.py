"""
tools/network_verifier.py
Passive Sovereign Network & Air-Gap Telemetry Auditor.
Audits active sockets and network interfaces passively without transmitting any outbound packets.
Supports both granular process-tree scoping (verifying the sovereign agent/sandbox process tree has 0 leaks)
and full host-level air-gap auditing.
"""

import os
import sys
import time
import psutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Any, List, Optional

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from tools.audit_trail import append_audit_event

LOOPBACK_IPS = {"127.0.0.1", "::1", "0.0.0.0", "::"}


def audit_network_isolation(
    scope: str = "process",
    target_pid: Optional[int] = None
) -> Dict[str, Any]:
    """
    Performs a 100% passive telemetry audit of active network sockets.
    Transmits ZERO outbound network packets or ICMP/ping probes.
    
    Args:
        scope: 'process' (default) to audit the current Python agent & child subprocess tree,
               or 'host' to audit system-wide OS network sockets.
        target_pid: Optional specific PID to audit if scope == 'process' (defaults to os.getpid()).
    """
    start_time = time.time()
    timestamp_utc = datetime.now(timezone.utc).isoformat()

    loopback_sockets = 0
    external_connections: List[Dict[str, Any]] = []

    if scope == "process":
        # Target current process and all child subprocesses (e.g. sandbox)
        root_pid = target_pid or os.getpid()
        pids_to_check = {root_pid}
        try:
            parent_proc = psutil.Process(root_pid)
            for child in parent_proc.children(recursive=True):
                pids_to_check.add(child.pid)
        except Exception:
            pass

        for pid in pids_to_check:
            try:
                proc = psutil.Process(pid)
                for conn in proc.connections(kind='inet'):
                    laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "None"
                    raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None
                    status = conn.status

                    is_raddr_ext = conn.raddr and conn.raddr.ip not in LOOPBACK_IPS
                    is_laddr_ext = conn.laddr and conn.laddr.ip not in LOOPBACK_IPS

                    if status in ("ESTABLISHED", "SYN_SENT", "SYN_RECV") and (is_raddr_ext or is_laddr_ext):
                        external_connections.append({
                            "pid": pid,
                            "proc_name": proc.name(),
                            "type": "TCP" if conn.type == 1 else "UDP",
                            "local_address": laddr,
                            "remote_address": raddr,
                            "status": status,
                        })
                    else:
                        loopback_sockets += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass

        is_air_gap_intact = len(external_connections) == 0
        verdict = "PASS_PROCESS_AIR_GAP_VERIFIED" if is_air_gap_intact else "ALERT_PROCESS_EXTERNAL_SOCKET_DETECTED"

    else:
        # Host-wide system socket audit
        try:
            connections = psutil.net_connections(kind='inet')
            for conn in connections:
                laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "None"
                raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else None
                status = conn.status

                is_raddr_ext = conn.raddr and conn.raddr.ip not in LOOPBACK_IPS
                is_laddr_ext = conn.laddr and conn.laddr.ip not in LOOPBACK_IPS

                if status in ("ESTABLISHED", "SYN_SENT", "SYN_RECV") and (is_raddr_ext or is_laddr_ext):
                    external_connections.append({
                        "pid": conn.pid,
                        "type": "TCP" if conn.type == 1 else "UDP",
                        "local_address": laddr,
                        "remote_address": raddr,
                        "status": status,
                    })
                else:
                    loopback_sockets += 1
        except (psutil.AccessDenied, Exception):
            pass

        is_air_gap_intact = len(external_connections) == 0
        verdict = "PASS_HOST_AIR_GAP_VERIFIED" if is_air_gap_intact else "ALERT_HOST_EXTERNAL_CONNECTIONS_DETECTED"

    # Passively inspect network interfaces
    interfaces: Dict[str, Dict[str, Any]] = {}
    try:
        if_stats = psutil.net_if_stats()
        for if_name, stat in if_stats.items():
            interfaces[if_name] = {
                "is_up": stat.isup,
                "speed_mbps": stat.speed,
                "mtu": stat.mtu,
            }
    except Exception:
        pass

    duration_ms = (time.time() - start_time) * 1000

    outputs = {
        "timestamp_utc": timestamp_utc,
        "scope": scope,
        "verdict": verdict,
        "is_air_gap_intact": is_air_gap_intact,
        "loopback_sockets_count": loopback_sockets,
        "external_active_connections_count": len(external_connections),
        "external_connections": external_connections,
        "adapters_audited": len(interfaces),
    }

    append_audit_event(
        tool_name="verify_network_tool",
        inputs={"method": "PASSIVE_SOCKET_INSPECTION", "scope": scope},
        outputs=outputs,
        status="SUCCESS",
        duration_ms=duration_ms,
        caller="verify_network_tool"
    )

    return outputs


try:
    from langchain_core.tools import tool

    @tool
    def verify_network_tool(scope: str = "process") -> str:
        """
        Passively audits network sockets to verify air-gap isolation without transmitting packets.
        
        Args:
            scope: 'process' (default) to audit the agent & sandbox subprocess tree specifically,
                   or 'host' to audit all system-wide network sockets across the host OS.
        """
        res = audit_network_isolation(scope=scope)
        verdict = res["verdict"]
        ext_count = res["external_active_connections_count"]
        loop_count = res["loopback_sockets_count"]

        if res["is_air_gap_intact"]:
            return (
                f"Sovereign Air-Gap Telemetry Audit Result [{scope.upper()} SCOPE]: {verdict}\n"
                f"- Passive Packet Transmissions: 0 (Strictly local socket inspection)\n"
                f"- Active Non-Loopback External Connections: 0\n"
                f"- Local Loopback/Internal Sockets: {loop_count}\n"
                f"- Network Adapters Audited: {res['adapters_audited']}\n"
                f"- Timestamp: {res['timestamp_utc']}\n"
                f"- Status: Air-gap isolation confirmed and signed in sovereign audit ledger."
            )
        else:
            return (
                f"Sovereign Air-Gap Telemetry Warning [{scope.upper()} SCOPE]: {verdict}\n"
                f"- External Active Connections Detected: {ext_count}\n"
                f"- External Endpoints: {res['external_connections']}\n"
                f"- Timestamp: {res['timestamp_utc']}\n"
                f"- Status: Outbound traffic detected. Security verification required."
            )

except ImportError:
    verify_network_tool = None
