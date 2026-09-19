# Document Generator Template Registry

## Overview
When the Supervisor Agent or Coder Agent uses the `doc_generator.py` tool, it MUST provide a `template_type` and a dynamically constructed `payload` dictionary containing the required keys for that specific template. 

This document serves as the official schema mapping for all Enterprise Templates. If the agent fails to provide the required keys in the payload, the resulting `.docx` file will have blank tags (e.g. `{{ vendor_name }}` will remain unrendered), which is an unacceptable audit failure.

## Required Payload Keys by Template

### 1. `NFA_Emergency_Procurement`
* **Purpose:** Generating official Notes for Approval for emergency purchases based on inspection failures.
* **Required Payload Keys:**
  - `equipment_id`
  - `t_req_mm`
  - `measured_thickness_mm`
  - `status`
  - `audit_risk`
  - `sanction_clause`

### 2. `ASME_Turnaround_Inspection`
* **Purpose:** Standard ASME Section VIII statutory inspection reports.
* **Required Payload Keys:**
  - `equipment_id`
  - `corrosion_rate_mm_yr`
  - `remaining_life_years`
  - `inspector_name`

### 3. `PAC_Proprietary_Article_Certificate`
* **Purpose:** Sole-source justification procurement document.
* **Required Payload Keys:**
  - `vendor_name`
  - `equipment_id`
  - `justification_clause`
  - `estimated_cost`

### 4. `Vendor_Blacklist_Notice`
* **Purpose:** Official termination/suspension notice for non-compliant vendors.
* **Required Payload Keys:**
  - `vendor_name`
  - `violation_details`
  - `suspension_period_months`
  - `authority_name`

### 5. `API_510_Remaining_Life_Report`
* **Purpose:** API 510 Fitness for Service (FFS) Evaluation.
* **Required Payload Keys:**
  - `equipment_id`
  - `measured_thickness_mm`
  - `t_min_mm`
  - `remaining_life_years`
  - `next_inspection_date`

### 6. `CVC_Audit_Compliance_Report`
* **Purpose:** Quarterly Central Vigilance Commission (CVC) compliance status.
* **Required Payload Keys:**
  - `audit_quarter`
  - `total_tenders`
  - `deviations_found`
  - `compliance_score`

### 7. `Material_Deviation_Approval`
* **Purpose:** Requesting approval to deviate from design materials.
* **Required Payload Keys:**
  - `equipment_id`
  - `original_material`
  - `proposed_material`
  - `metallurgist_name`
  - `approval_status`

### 8. `Hot_Work_Permit_Authorization`
* **Purpose:** High-risk plant maintenance authorization.
* **Required Payload Keys:**
  - `location`
  - `equipment_id`
  - `contractor_name`
  - `hazard_level`
  - `valid_until`

### 9. `Incident_Root_Cause_Analysis`
* **Purpose:** Statutory RCA investigation report.
* **Required Payload Keys:**
  - `incident_date`
  - `equipment_id`
  - `failure_mode`
  - `rca_summary`
  - `corrective_action`

### 10. `Executive_Summary_Brief`
* **Purpose:** High-level plant integrity and risk summary for management.
* **Required Payload Keys:**
  - `report_date`
  - `critical_breaches`
  - `upcoming_turnarounds`
  - `capex_required`

## Universal System Tags
The `doc_generator.py` Python engine automatically injects the following keys into every template. The LLM does **not** need to include these in the payload:
- `date_generated` (Current system timestamp)
- `document_hash` (The immutable SHA-256 seal)
