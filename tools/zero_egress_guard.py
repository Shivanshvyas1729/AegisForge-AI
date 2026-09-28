"""
Alias module redirecting zero_egress_guard to tools.network_verifier.
Maintains backward compatibility across all agents and services.
"""

from tools.network_verifier import NetworkVerifier, verify_zero_egress

__all__ = ["NetworkVerifier", "verify_zero_egress"]
