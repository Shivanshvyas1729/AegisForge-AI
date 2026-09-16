import streamlit as st
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
from tools.asme_calculator import evaluate_vessel_integrity
from schemas.mvp_schema import InspectionInput
from config.settings import logger

def send_to_workbench_for_compliance(eq_id, t_req, t_actual, delta, mawp, breach_status):
    """
    Data Bridge: Formulates a prompt based on deterministic calc results
    and injects it into the AI Workbench session state for compliance analysis.
    """
    status_str = "BREACHED" if breach_status else "PASSED"
    prompt = (
        f"The vessel {eq_id} has {status_str} statutory ASME UG-27 minimum thickness.\n"
        f"Required: {t_req:.2f} mm\n"
        f"Measured: {t_actual:.2f} mm\n"
        f"Margin Delta: {delta:.2f} mm\n"
        f"Derated MAWP: {mawp:.1f} barg\n\n"
        f"Based on this, evaluate if an emergency single-source procurement "
        f"for an OEM weld overlay repair complies with Central Vigilance Commission "
        f"(CVC) Circular 02/02/2004 and DOP Clause 4.2. Also, generate the formal Note for Approval."
    )
    st.session_state.chat_pending_prompt = prompt
    st.toast("Data bridged to AI Workbench! Switch to the Workbench tab to continue.", icon="🔗")

def render_calculator_tab():
    st.markdown("## 🧮 ASME Section VIII & API 510 Calculator")
    st.markdown("Deterministic engineering verification — no LLM involved. Pure math.")

    col_params, col_results = st.columns([1, 1.2])

    with col_params:
        st.markdown('<p class="section-header">Input Parameters</p>', unsafe_allow_html=True)
        
        calc_eq_id = st.text_input("Equipment ID", value="11-V-102", key="calc_eq_id")
        calc_p = st.number_input("Design Pressure P (MPa)", min_value=0.1, max_value=50.0, value=14.5, step=0.5, key="calc_p")
        calc_r = st.number_input("Inside Radius R (mm)", min_value=100.0, max_value=5000.0, value=1200.0, step=50.0, key="calc_r")
        calc_s = st.number_input("Allowable Stress S (MPa)", min_value=10.0, max_value=300.0, value=118.0, step=1.0, key="calc_s")
        calc_e = st.selectbox("Joint Efficiency E", [1.0, 0.85, 0.70], index=0, key="calc_e")
        calc_t = st.number_input("Measured Wall Thickness (mm)", min_value=1.0, max_value=500.0, value=138.20, step=0.1, key="calc_t")
        calc_cr = st.number_input("Corrosion Rate (mm/year)", min_value=0.01, max_value=5.0, value=0.75, step=0.05, key="calc_cr")

    with col_results:
        st.markdown('<p class="section-header">Verification Results</p>', unsafe_allow_html=True)

        custom_input = InspectionInput(
            equipment_id=calc_eq_id,
            equipment_name="Interactive Vessel",
            design_pressure_mpa=calc_p,
            inside_radius_mm=calc_r,
            allowable_stress_mpa=calc_s,
            joint_efficiency=calc_e,
            measured_thickness_mm=calc_t,
            critical_location="Shell",
            corrosion_rate_mm_yr=calc_cr,
        )
        custom_calc = evaluate_vessel_integrity(custom_input)

        # Metrics
        m1, m2 = st.columns(2)
        with m1:
            st.metric("Required t_min", f"{custom_calc.t_req_mm:.2f} mm")
            st.metric("Measured Thickness", f"{custom_calc.measured_thickness_mm:.2f} mm")
        with m2:
            delta_color = "normal" if custom_calc.delta_mm >= 0 else "inverse"
            st.metric("Margin Δ", f"{custom_calc.delta_mm:.2f} mm", delta=f"{custom_calc.delta_mm:.2f} mm", delta_color=delta_color)
            st.metric("Derated MAWP", f"{custom_calc.derated_mawp_bar:.1f} barg")

        # Verdict
        if custom_calc.is_breach:
            st.error(
                f"🚨 **STATUTORY CODE BREACH**\n\n"
                f"Measured ({custom_calc.measured_thickness_mm:.2f} mm) is below ASME minimum "
                f"({custom_calc.t_req_mm:.2f} mm) by **{abs(custom_calc.delta_mm):.2f} mm**. "
                f"Remaining life: **{custom_calc.remaining_life_years:.2f} years**."
            )
        else:
            st.success(
                f"✅ **VESSEL COMPLIANT**\n\n"
                f"Margin: **+{custom_calc.delta_mm:.2f} mm**. "
                f"Safe operating life: **{custom_calc.remaining_life_years:.2f} years**."
            )

        # Formula proof
        st.markdown("---")
        st.markdown("#### 📐 ASME UG-27 Formula")
        st.latex(r"t_{\text{req}} = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P}")
        st.markdown(
            f"$t_{{\\text{{req}}}} = \\frac{{{calc_p} \\cdot {calc_r}}}{{{calc_s} \\cdot {calc_e} - 0.6 \\cdot {calc_p}}} "
            f"= {custom_calc.t_req_mm:.2f}\\text{{ mm}}$"
        )
        
        # New Data Bridge feature
        if st.button("🔗 Send Results to AI Workbench for CVC Audit", type="secondary", use_container_width=True):
            send_to_workbench_for_compliance(
                calc_eq_id, 
                custom_calc.t_req_mm, 
                custom_calc.measured_thickness_mm, 
                custom_calc.delta_mm,
                custom_calc.derated_mawp_bar,
                custom_calc.is_breach
            )

        # Export buttons
        st.markdown("---")
        st.markdown("#### 📥 Export Calculation Note")

        calc_cache_tuple = (calc_eq_id, calc_p, calc_r, calc_s, calc_e, calc_t, calc_cr)
        if st.session_state.get("last_calc_cache_tuple") != calc_cache_tuple:
            st.session_state.calc_docx_bytes = None
            st.session_state.calc_pdf_bytes = None
            st.session_state.last_calc_cache_tuple = calc_cache_tuple

        col_gen, col_dl1, col_dl2 = st.columns([1.5, 1, 1])

        with col_gen:
            if st.button("📄 Generate Deliverables", key="btn_gen_calc_docs", type="primary", use_container_width=True):
                with st.spinner("Compiling Note for Approval..."):
                    try:
                        from tools.doc_generator import generate_docx_deliverable, generate_pdf_deliverable
                        from schemas.mvp_schema import ReasoningOutput

                        calc_reasoning = ReasoningOutput(
                            executive_summary=(
                                f"ASME Sec VIII assessment for {calc_eq_id}. "
                                f"Status: {custom_calc.status}, delta {custom_calc.delta_mm:.2f} mm."
                            ),
                            cvc_guideline_clause=(
                                "CVC Circular 02/02/2004 Emergency Procurement." if custom_calc.is_breach
                                else "Routine turnaround maintenance."
                            ),
                            recommended_action=(
                                f"Emergency weld overlay repair, derate to {custom_calc.derated_mawp_bar:.1f} barg." if custom_calc.is_breach
                                else f"Continue operation at {custom_calc.design_pressure_bar:.1f} barg."
                            ),
                            estimated_cost="Rs. 88.0 Lakhs" if custom_calc.is_breach else "Routine Opex",
                            raw_model_response="Calculator export.",
                        )
                        calc_docx = generate_docx_deliverable(custom_input, custom_calc, calc_reasoning)
                        calc_pdf = generate_pdf_deliverable(custom_input, custom_calc, calc_reasoning)

                        with open(calc_docx["path"], "rb") as f_dx:
                            st.session_state.calc_docx_bytes = f_dx.read()
                        with open(calc_pdf["path"], "rb") as f_px:
                            st.session_state.calc_pdf_bytes = f_px.read()
                        st.success("Deliverables ready!")
                    except Exception as e:
                        logger.exception("Failed to compile documents in UI ASME Calculator.")
                        st.error(f"Failed to generate documents: {e}")

        if st.session_state.get("calc_docx_bytes"):
            with col_dl1:
                st.download_button(
                    "📥 Download .docx",
                    data=st.session_state.calc_docx_bytes,
                    file_name=f"{calc_eq_id}_Note.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                    key="calc_dl_docx",
                )
            with col_dl2:
                st.download_button(
                    "📥 Download .pdf",
                    data=st.session_state.calc_pdf_bytes,
                    file_name=f"{calc_eq_id}_Note.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    key="calc_dl_pdf",
                )
        else:
            st.caption("Click 'Generate Deliverables' to compile formal DOCX & PDF notes on-demand.")
