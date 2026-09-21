"""
Docker Sandbox Daemon & Isolated Code Execution Service
======================================================
Manages container daemon lifecycle and executes Python workloads with smart executive titles.
"""

from typing import Dict, Any, Optional
from tools.docker_sandbox import (
    is_daemon_running,
    start_daemon,
    stop_daemon,
    execute_in_sandbox,
)


class SandboxService:
    """Service for managing secure execution in air-gapped Docker sandbox containers."""

    def is_daemon_active(self) -> bool:
        """Returns True if the background Docker sandbox daemon is running."""
        return is_daemon_running()

    def start_container_daemon(self) -> bool:
        """Launches the Docker sandbox daemon container."""
        return start_daemon()

    def stop_container_daemon(self) -> bool:
        """Terminates and cleans up the Docker sandbox daemon container."""
        return stop_daemon()

    def run_code_in_docker(self, code_string: str, task_title: Optional[str] = None) -> Dict[str, Any]:
        """
        Executes Python code in the Docker sandbox daemon with smart titling.
        """
        payload = {"code_string": code_string}
        if task_title:
            payload["task_title"] = task_title
        return execute_in_sandbox.invoke(payload)

    def run_code_subprocess(self, code_string: str, timeout: int = 15) -> Dict[str, Any]:
        """
        Executes code through the security-verified sandbox tool.
        """
        return execute_in_sandbox.invoke({"code_string": code_string, "task_title": "Isolated Subprocess Execution"})

