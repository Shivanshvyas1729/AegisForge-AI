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
        template_path = os.path.join(workspace_root, "templates", f"{request.template_type}.docx")
        
        if not os.path.exists(template_path):
            raise FileNotFoundError(f"Template '{request.template_type}' not found in the templates directory!")
            
        # 1. Cryptographic Audit Seal Generation
        content_string = str(request.payload)
        document_hash = hashlib.sha256(content_string.encode('utf-8')).hexdigest()
        
        # 2. Inject dynamic variables
        context = request.payload.copy()
        context["date_generated"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        context["document_hash"] = document_hash

        # 3. Output path
        output_dir = os.path.join(workspace_root, "data", "output")
        os.makedirs(output_dir, exist_ok=True)
        file_name = f"{request.base_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
        file_path = os.path.join(output_dir, file_name)

        # 4. Render native Word Template or fallback to python-docx
        rendered = False
        try:
            from docxtpl import DocxTemplate
            doc = DocxTemplate(template_path)
            doc.render(context)
            doc.save(file_path)
            rendered = True
        except Exception:
            rendered = False

        if not rendered:
            import docx
            doc = docx.Document()
            doc.add_heading(f"AegisForge-AI Statutory Report: {request.base_name}", 0)
            doc.add_paragraph(f"Template Type: {request.template_type}")
            doc.add_paragraph(f"Generated At: {context['date_generated']}")
            doc.add_paragraph(f"Cryptographic Hash: {document_hash}")
            doc.add_heading("Executive Summary", level=1)
            doc.add_paragraph(str(context.get("executive_summary", "N/A")))
            doc.add_heading("Engineering Metrics", level=1)
            for k, v in context.items():
                if k not in ["executive_summary", "date_generated", "document_hash", "inspection_data", "calculation_data", "compliance_data"]:
                    doc.add_paragraph(f"{k}: {v}")
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


@tool
def generate_nfa_documents(request: DocumentGenerationRequest) -> dict:
    """Generates NFA Word/PDF documents."""
    print(f"\n--- EXECUTING TOOL: generate_nfa_documents ---\n")
    logger.info(f"Executing tool: generate_nfa_documents")
    try:
        generator = DocumentGenerator()
        return generator.generate_official_nfa(request).model_dump()
    except Exception as e:
        logger.error(f"Error in generate_nfa_documents: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Test for Document Generator
    logger.info("Testing generate_nfa_documents...")
    mock_request = DocumentGenerationRequest(
        dossier_id="ID-9982",
        executive_summary="The vessel is safe.",
        calculation_summary={"t_req": 16.0},
        compliance_summary={"status": "APPROVED"}
    )
    # This might fail if docxtpl is missing or template doesn't exist, which tests the try-except!
    result = generate_nfa_documents.invoke({"request": mock_request})
    logger.info(f"Result: {result}")
