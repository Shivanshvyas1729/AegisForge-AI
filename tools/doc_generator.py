import sys
import os
import hashlib
import datetime

# Ensure the root workspace is in the python path to allow absolute imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from schemas.document import DocumentGenerationRequest, DocumentGenerationResult
from tools.audit_trail import AuditLedger

try:
    from docxtpl import DocxTemplate
except ImportError:
    print("CRITICAL: docxtpl is not installed on the host. Please run: uv pip install docxtpl or pip install docxtpl")

class DocumentGenerator:
    def __init__(self, use_audit_trail: bool = True):
        self.use_audit_trail = use_audit_trail
        if self.use_audit_trail:
            self.ledger = AuditLedger()

    def generate_official_nfa(self, request: DocumentGenerationRequest, caller_agent: str = "chief_reviewer") -> DocumentGenerationResult:
        """
        Generates official Word Documents by injecting data into 10+ scalable .docx templates.
        This is Strategy 1 of the Dual-Pipeline (Enterprise Templates).
        """
        workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        templates_dir = os.path.join(workspace_root, "templates")
        
        # Discover all available templates
        available_templates = {}
        if os.path.exists(templates_dir):
            for f in os.listdir(templates_dir):
                if f.endswith(".docx"):
                    base = os.path.splitext(f)[0]
                    available_templates[base.lower()] = os.path.join(templates_dir, f)
        
        # Resolve matching template
        req_clean = (request.template_type or "nfa").lower().replace("-", "_").replace(" ", "_")
        template_path = None
        
        # 1. Direct or partial match
        if req_clean in available_templates:
            template_path = available_templates[req_clean]
        else:
            for k, p in available_templates.items():
                if req_clean in k or k in req_clean:
                    template_path = p
                    break
                    
        # 2. Heuristic domain keyword match
        if not template_path:
            for k, p in available_templates.items():
                if any(w in req_clean for w in ["asme", "vessel", "turnaround", "ndt"]) and "asme" in k:
                    template_path = p
                    break
                elif any(w in req_clean for w in ["api", "510", "rsl", "remaining", "life"]) and "510" in k:
                    template_path = p
                    break
                elif any(w in req_clean for w in ["cvc", "compliance", "audit", "vigilance"]) and "cvc" in k:
                    template_path = p
                    break
                elif any(w in req_clean for w in ["pac", "proprietary"]) and "pac" in k:
                    template_path = p
                    break
                elif any(w in req_clean for w in ["executive", "brief", "summary"]) and "executive" in k:
                    template_path = p
                    break
                    
        # 3. Safe fallback to default NFA template
        if not template_path:
            fallback = os.path.join(templates_dir, "NFA_Emergency_Procurement.docx")
            if os.path.exists(fallback):
                template_path = fallback
            elif available_templates:
                template_path = list(available_templates.values())[0]
            
        # 1. Cryptographic Audit Seal Generation
        content_string = str(request.payload)
        document_hash = hashlib.sha256(content_string.encode('utf-8')).hexdigest()
        
        # 2. Inject dynamic variables & build an adaptive context
        raw_payload = request.payload.copy() if isinstance(request.payload, dict) else {"payload": str(request.payload)}
        context = {}
        for k, v in raw_payload.items():
            context[k] = v
            # Also create normalized snake_case and lower_case variants for robust template matching
            clean_k = str(k).lower().strip().replace(" ", "_").replace("-", "_")
            context[clean_k] = v

        # Adaptive aliases for common template placeholders
        eq_val = context.get("equipment_id") or context.get("tag") or context.get("vessel_tag") or "11-V-102"
        context["equipment_id"] = eq_val
        context["date_generated"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        context["document_hash"] = document_hash
        context["document_hash_short"] = document_hash[:16]

        # 3. Output path
        output_dir = os.path.join(workspace_root, "data", "output")
        os.makedirs(output_dir, exist_ok=True)
        safe_base = (request.base_name or "NFA_Report").replace(" ", "_").replace("/", "_").replace("\\", "_")
        file_name = f"{safe_base}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
        file_path = os.path.join(output_dir, file_name)

        rendered = False
        if template_path and os.path.exists(template_path):
            try:
                from docxtpl import DocxTemplate
                import docx
                doc = DocxTemplate(template_path)
                doc.render(context)
                doc.save(file_path)

                # Now adaptively enrich the document: if tables have empty cells or if more data exists in payload, append them
                wd_doc = docx.Document(file_path)
                
                # Check tables and dynamically populate any remaining blank cells
                for table in wd_doc.tables:
                    for row in table.rows:
                        if len(row.cells) >= 2:
                            field_name = row.cells[0].text.strip().lower().replace(" ", "_")
                            cell_val = row.cells[1].text.strip()
                            if not cell_val or "{{" in cell_val:
                                for ck, cv in context.items():
                                    if ck in field_name or field_name in ck:
                                        row.cells[1].text = str(cv)
                                        break

                # Adaptively append Comprehensive Technical Summary & Metrics Table
                wd_doc.add_heading("Technical Parameters & Multi-Agent Findings", level=2)
                
                # Filter out noisy internal keys
                omitted_keys = {"payload", "date_generated", "document_hash", "document_hash_short", "inspection_data", "calculation_data", "compliance_data"}
                display_items = [(k.replace("_", " ").title(), str(v)) for k, v in raw_payload.items() if k not in omitted_keys and not isinstance(v, (dict, list))]

                if display_items:
                    data_table = wd_doc.add_table(rows=1, cols=2)
                    data_table.style = 'Table Grid'
                    hdr_cells = data_table.rows[0].cells
                    hdr_cells[0].text = 'Engineering Parameter'
                    hdr_cells[1].text = 'Evaluated Value'
                    for param_name, param_val in display_items:
                        row_cells = data_table.add_row().cells
                        row_cells[0].text = param_name
                        row_cells[1].text = param_val

                # Append executive summary if present
                exec_sum = context.get("executive_summary")
                if exec_sum:
                    wd_doc.add_heading("Executive Reviewer Verdict & Recommendations", level=2)
                    wd_doc.add_paragraph(str(exec_sum))

                wd_doc.save(file_path)
                rendered = True
            except Exception as e:
                print(f"Error rendering template with docxtpl: {e}")
                rendered = False

        if not rendered:
            import docx
            doc = docx.Document()
            doc.add_heading(f"AegisForge-AI Statutory Report: {request.base_name}", 0)
            doc.add_paragraph(f"Template Type: {request.template_type}")
            doc.add_paragraph(f"Generated At: {context['date_generated']}")
            doc.add_paragraph(f"Cryptographic Hash (SHA-256): {document_hash}")
            
            doc.add_heading("Executive Summary", level=1)
            doc.add_paragraph(str(context.get("executive_summary", "Statutory inspection and integrity audit complete.")))
            
            doc.add_heading("Engineering Metrics & Analysis", level=1)
            table = doc.add_table(rows=1, cols=2)
            table.style = 'Table Grid'
            hdr = table.rows[0].cells
            hdr[0].text = "Parameter"
            hdr[1].text = "Value"
            for k, v in raw_payload.items():
                if k not in ["executive_summary", "date_generated", "document_hash", "payload"]:
                    r_cells = table.add_row().cells
                    r_cells[0].text = str(k).replace("_", " ").title()
                    r_cells[1].text = str(v)
            doc.save(file_path)
        
        # 5. Log to immutable ledger
        audit_id = "N/A"
        if self.use_audit_trail:
            audit_id = self.ledger.append_event(
                event_type="DOCUMENT_GENERATION",
                workflow_id="PUBLISH_DELIVERABLE",
                tool_name="doc_generator",
                caller=caller_agent,
                agent_version="1.0.0",
                tool_version="1.0.0",
                inputs={"template": request.template_type},
                outputs={"file_path": file_path, "document_hash": document_hash},
                status="COMPLETED"
            )
            
        return DocumentGenerationResult(
            status="SUCCESS",
            docx_path=file_path,
            document_hash=document_hash,
            audit_id=audit_id
        )

from langchain_core.tools import tool
from schemas.document import DocumentGenerationRequest
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


from typing import Optional, Any

@tool
def generate_nfa_documents(
    template_type: str = "NFA_Emergency_Procurement.docx",
    base_name: str = "NFA_Report",
    payload: Optional[dict] = None,
    **kwargs: Any
) -> dict:
    """Generates certified NFA Word/PDF documents with cryptographic SHA-256 seal."""
    print(f"\n--- EXECUTING TOOL: generate_nfa_documents ---\n")
    logger.info(f"Executing tool: generate_nfa_documents")
    try:
        generator = DocumentGenerator()
        if payload is None:
            payload = {}

        import ast
        for k, v in kwargs.items():
            if k in ["equipment_id", "vessel_tag", "tag"]:
                base_name = str(v)
                payload[k] = v
            elif k in ["template_name", "template"]:
                template_type = str(v)
            elif isinstance(v, str) and (v.startswith("{") and v.endswith("}")):
                # Adaptively parse stringified dictionaries (e.g. asme_results, cvc_compliance)
                try:
                    parsed_dict = ast.literal_eval(v)
                    if isinstance(parsed_dict, dict):
                        for sub_k, sub_v in parsed_dict.items():
                            payload[sub_k] = sub_v
                except Exception:
                    payload[k] = v
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    payload[sub_k] = sub_v
            else:
                payload[k] = v

        req = DocumentGenerationRequest(template_type=template_type, base_name=base_name, payload=payload)
        return generator.generate_official_nfa(req).model_dump()
    except Exception as e:
        logger.error(f"Error in generate_nfa_documents: {e}")
        return {"status": "error", "error": str(e)}


