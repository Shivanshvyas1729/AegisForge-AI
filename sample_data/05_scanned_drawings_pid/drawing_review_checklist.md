# REFINERY ENGINEERING DRAWING & P&ID QA/QC CHECKLIST
## Process Safety Management (PSM) & HAZOP Verification Protocol

**Drawing Reviewed:** `GHR-CDU1-PID-104` (Rev 04)  
**Evaluator Target:** Multimodal Vision Model (e.g. Qwen2-VL, InternVL-2)  
**Standard Benchmarking Questions for AI Workbench:**

---

### Phase 1: Symbol & Tag Optical Extraction
- [ ] **Check 1.1:** Has the model correctly detected and extracted equipment tags: `11-TK-01`, `11-P-101A`, `11-E-101`, and `11-V-101`?
- [ ] **Check 1.2:** Has the model parsed the ISA-5.1 circular bubbles and identified instrument functions (`PT-101` = Pressure Transmitter, `FT-101` = Flow Transmitter, `FIC-101` = Flow Controller, `TT-102` = Temperature Transmitter)?
- [ ] **Check 1.3:** Is the overpressure protection device correctly identified as `PSV-101` with set point `12.5 barg` discharging to Flare Header?

### Phase 2: Flow Line Connectivity & Topology
- [ ] **Check 2.1:** Verify pipeline sequence: Does `6"-CR-1001-A1A` feed the suction of pump `11-P-101A` from tank `11-TK-01`?
- [ ] **Check 2.2:** Verify control loop association: Does `FIC-101` modulate control valve `FCV-101` located on line `6"-CR-1002-A1A`?
- [ ] **Check 2.3:** Does the bottom effluent line from Desalter `11-V-101` correctly route sour water to the stripper column via `4"-SW-2001`?

### Phase 3: Operational Safety & Compliance Flags
- [ ] **Check 3.1:** Verify fail-safe position of `FCV-101` (Must be Fail-Closed "FC" to prevent overfilling downstream desalter upon loss of air).
- [ ] **Check 3.2:** Confirm suction manual isolation gate valve presence upstream of charge pump `11-P-101A`.
- [ ] **Check 3.3:** Flag whether thermal relief valve (TRV) is noted on the shell & tube exchanger isolation block.

---
**Verdict Criteria:**
- **Full Pass:** All 9 checklist items verified autonomously with 100% tag accuracy and zero hallucinated tags.
