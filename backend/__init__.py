"""
AegisForge-AI: Sovereign Air-Gapped Backend Architecture
=======================================================
Enterprise backend package providing decoupled services and a unified facade for UI and CLI.
"""

from .app_backend import AegisForgeBackend
from .services.dossier_service import DossierService
from .services.engineering_service import EngineeringService
from .services.compliance_service import ComplianceService
from .services.telemetry_service import TelemetryService
from .services.sandbox_service import SandboxService
from .services.audit_service import AuditService
from .services.langfuse_service import LangfuseService


def get_backend(workspace_root=None) -> AegisForgeBackend:
    """Convenience factory function returning the backend gateway."""
    import importlib
    import backend.app_backend
    importlib.reload(backend.app_backend)
    from backend.app_backend import AegisForgeBackend
    return AegisForgeBackend(workspace_root)



__all__ = [
    "AegisForgeBackend",
    "get_backend",
    "DossierService",
    "EngineeringService",
    "ComplianceService",
    "TelemetryService",
    "SandboxService",
    "AuditService",
    "LangfuseService",
]

