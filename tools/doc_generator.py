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
            
        # 1. Load the native Word Document Template
        doc = DocxTemplate(template_path)
        
        # 2. Cryptographic Audit Seal Generation
        # We pseudo-hash the payload to seal the exact inputs used to generate this document
        content_string = str(request.payload)
        document_hash = hashlib.sha256(content_string.encode('utf-8')).hexdigest()
        
        # 3. Inject dynamic variables into the Word Document
        # We merge the LLM's generic payload with our system-generated universal variables
        context = request.payload.copy()
        context["date_generated"] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        context["document_hash"] = document_hash
        
        doc.render(context)
        
        # 4. Save the document
        output_dir = os.path.join(workspace_root, "data", "output")
        os.makedirs(output_dir, exist_ok=True)
        
        file_name = f"{request.base_name}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.docx"
        file_path = os.path.join(output_dir, file_name)
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
