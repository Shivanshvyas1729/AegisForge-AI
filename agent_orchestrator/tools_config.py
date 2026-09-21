import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from tools import (
    api_579_ffs_tool,
    asme_calculator,
    audit_trail,
    compliance_auditor,
    doc_generator,
    docker_sandbox,
    file_io,
    inspection_extractor_tool,
    material_lookup_tool,
    network_verifier,
    risk_based_inspection_tool,
    routing_guard,
    thickness_grid_analyzer,
)

# Vision Agent Tools
vision_tools = [
    inspection_extractor_tool.extract_inspection_data,
    thickness_grid_analyzer.analyze_thickness_grid,
    file_io.read_scanned_pdf,
]

# Coder Agent Tools
coder_tools = [
    asme_calculator.calculate_asme_stresses,
    api_579_ffs_tool.run_ffs_assessment,
    material_lookup_tool.lookup_material,
    docker_sandbox.execute_in_sandbox,
]

# Reasoning / Compliance Agent Tools
reasoning_tools = [
    compliance_auditor.audit_cvc_compliance,
    risk_based_inspection_tool.calculate_rbi_score,
    routing_guard.verify_routing_policy,
]

# Publisher Agent Tools
publisher_tools = [
    doc_generator.generate_nfa_documents,
    audit_trail.write_sha256_audit_seal,
    network_verifier.verify_zero_egress,
]
