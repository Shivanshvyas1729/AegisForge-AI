"""
Langfuse Observability Container Lifecycle Service
===================================================
Manages local Langfuse container daemon lifecycle, status reporting,
and port discovery for air-gapped LLM tracing & observability.
"""

import os
import re
import json
import logging
import subprocess
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

DEFAULT_LANGFUSE_PORT = 3000
DEFAULT_WEB_CONTAINER_NAME = "langfuse-langfuse-web-1"


class LangfuseService:
    """Service for managing secure Langfuse observability container stack."""

    def __init__(self, workspace_root: Optional[Path] = None):
        if workspace_root is None:
            self.workspace_root = Path(__file__).resolve().parent.parent.parent
        else:
            self.workspace_root = Path(workspace_root)
        self.compose_file = self.workspace_root / "langfuse" / "docker-compose.yml"
        self._target_port = self._load_configured_port()

    def _load_configured_port(self) -> int:
        """Loads configured Langfuse port from .env or defaults to 3000."""
        env_file = self.workspace_root / ".env"
        if env_file.exists():
            try:
                for line in env_file.read_text(encoding="utf-8").splitlines():
                    if line.startswith("LANGFUSE_BASE_URL"):
                        val = line.split("=", 1)[1].strip().strip('"').strip("'")
                        match = re.search(r":(\d+)", val)
                        if match:
                            return int(match.group(1))
            except Exception:
                pass
        return DEFAULT_LANGFUSE_PORT

    def is_docker_available(self) -> bool:
        """Checks if Docker engine is reachable on the host."""
        try:
            res = subprocess.run(["docker", "info"], capture_output=True, text=True, timeout=5)
            return res.returncode == 0
        except Exception:
            return False

    def is_container_running(self) -> bool:
        """Returns True if the Langfuse web container is currently active."""
        info = self.get_container_info()
        return info.get("is_running", False)

    def get_container_info(self) -> Dict[str, Any]:
        """
        Inspects Docker for Langfuse containers and returns status, container ID,
        and mapped host/container port IDs.
        """
        result = {
            "docker_available": False,
            "is_running": False,
            "container_id": None,
            "container_name": DEFAULT_WEB_CONTAINER_NAME,
            "port": self._target_port,
            "port_id": str(self._target_port),
            "ports_display": f"{self._target_port}:3000",
            "url": f"http://localhost:{self._target_port}",
            "status": "STOPPED",
            "state": "exited",
            "health": "unknown",
            "services": [],
        }

        try:
            res = subprocess.run(
                ["docker", "ps", "-a", "--filter", "name=langfuse", "--format", "{{json .}}"],
                capture_output=True,
                text=True,
                timeout=8,
            )
            if res.returncode != 0:
                return result

            result["docker_available"] = True
            lines = [l.strip() for l in res.stdout.strip().splitlines() if l.strip()]

            web_container = None
            services_found = []

            for line in lines:
                try:
                    cdata = json.loads(line)
                    c_name = cdata.get("Names", "")
                    c_image = cdata.get("Image", "")
                    c_state = cdata.get("State", "").lower()
                    c_ports = cdata.get("Ports", "")

                    services_found.append({
                        "name": c_name,
                        "image": c_image,
                        "state": c_state,
                        "status": cdata.get("Status", ""),
                        "ports": c_ports,
                    })

                    # Identify the main Langfuse web UI container
                    if "web" in c_name.lower() or "langfuse/langfuse:" in c_image or "langfuse:4" in c_image:
                        web_container = cdata
                except Exception:
                    continue

            result["services"] = services_found

            if web_container:
                c_id = web_container.get("ID", "")[:12]
                c_name = web_container.get("Names", DEFAULT_WEB_CONTAINER_NAME)
                c_state = web_container.get("State", "").lower()
                c_status = web_container.get("Status", "")
                c_ports = web_container.get("Ports", "")
                c_health = web_container.get("HealthStatus", "none")

                is_up = c_state == "running"
                result["container_id"] = c_id
                result["container_name"] = c_name
                result["state"] = c_state
                result["status"] = c_status
                result["health"] = c_health
                result["is_running"] = is_up

                # Parse mapped port ID
                if c_ports:
                    result["ports_display"] = c_ports
                    # Look for pattern like 0.0.0.0:3000->3000/tcp or 127.0.0.1:3000->3000/tcp
                    match = re.search(r"(?:0\.0\.0\.0|127\.0\.0\.1|:::|\[::\])?:?(\d+)->(\d+)", c_ports)
                    if match:
                        result["port"] = int(match.group(1))
                        result["port_id"] = match.group(1)
                        result["container_port"] = match.group(2)
                    else:
                        match_single = re.search(r"(\d+)/tcp", c_ports)
                        if match_single:
                            result["port"] = int(match_single.group(1))
                            result["port_id"] = match_single.group(1)

                result["url"] = f"http://localhost:{result['port']}"
            else:
                result["status"] = "NOT INITIALIZED"

        except Exception as e:
            logger.debug(f"Could not query Docker for Langfuse info: {e}")

        # Final health verification via HTTP if reported running
        if result["is_running"]:
            try:
                req = urllib.request.Request(result["url"], method="GET")
                with urllib.request.urlopen(req, timeout=1.5) as resp:
                    if resp.status < 500:
                        result["http_accessible"] = True
            except Exception:
                result["http_accessible"] = False

        return result

    def start_container(self) -> Dict[str, Any]:
        """
        Starts the Langfuse container stack using Docker Compose or standalone docker start.
        """
        try:
            if self.compose_file.exists():
                cmd = ["docker", "compose", "-f", str(self.compose_file), "up", "-d"]
                res = subprocess.run(
                    cmd,
                    cwd=str(self.compose_file.parent),
                    capture_output=True,
                    text=True,
                    timeout=90,
                )
                if res.returncode == 0:
                    info = self.get_container_info()
                    return {
                        "success": True,
                        "message": f"Langfuse container stack started on port {info['port']}.",
                        "info": info,
                    }
                else:
                    err = res.stderr.strip() or res.stdout.strip()
                    # Fallback to direct container start if compose throws warning/error
                    fallback_res = subprocess.run(
                        ["docker", "start", DEFAULT_WEB_CONTAINER_NAME],
                        capture_output=True,
                        text=True,
                        timeout=30,
                    )
                    if fallback_res.returncode == 0:
                        info = self.get_container_info()
                        return {
                            "success": True,
                            "message": f"Langfuse web container started on port {info['port']}.",
                            "info": info,
                        }
                    return {"success": False, "error": err or fallback_res.stderr.strip()}
            else:
                res = subprocess.run(
                    ["docker", "start", DEFAULT_WEB_CONTAINER_NAME],
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if res.returncode == 0:
                    info = self.get_container_info()
                    return {
                        "success": True,
                        "message": f"Langfuse container started on port {info['port']}.",
                        "info": info,
                    }
                return {"success": False, "error": res.stderr.strip()}
        except Exception as e:
            logger.error(f"Error starting Langfuse container: {e}")
            return {"success": False, "error": str(e)}

    def stop_container(self) -> Dict[str, Any]:
        """
        Stops the Langfuse container stack.
        """
        try:
            if self.compose_file.exists():
                cmd = ["docker", "compose", "-f", str(self.compose_file), "stop"]
                res = subprocess.run(
                    cmd,
                    cwd=str(self.compose_file.parent),
                    capture_output=True,
                    text=True,
                    timeout=30,
                )
                if res.returncode == 0:
                    return {"success": True, "message": "Langfuse container stack stopped successfully."}

            res = subprocess.run(
                ["docker", "stop", DEFAULT_WEB_CONTAINER_NAME],
                capture_output=True,
                text=True,
                timeout=20,
            )
            return {"success": True, "message": "Langfuse container stopped."}
        except Exception as e:
            logger.error(f"Error stopping Langfuse container: {e}")
            return {"success": False, "error": str(e)}
