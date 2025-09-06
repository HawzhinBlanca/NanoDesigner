from __future__ import annotations

import os
import tempfile
from typing import List, Optional

try:
    from google.cloud import documentai_v1 as documentai
except ImportError:
    # Mock Document AI if not installed
    class MockDocument:
        def __init__(self):
            self.text = ""
            self.pages = []
            
        class Page:
            def __init__(self):
                self.paragraphs = []
                
            class Layout:
                def __init__(self):
                    self.text_anchor = None
    
    class MockDocumentAI:
        Document = MockDocument
        
        class DocumentProcessorServiceClient:
            def processor_path(self, *args):
                return "mock-processor-path"
                
            def process_document(self, request):
                result = type('obj', (object,), {'document': MockDocument()})()
                return result
        
        class RawDocument:
            def __init__(self, content=None, mime_type=None):
                self.content = content
                self.mime_type = mime_type
                
        class ProcessRequest:
            def __init__(self, name=None, raw_document=None):
                self.name = name
                self.raw_document = raw_document
    
    documentai = MockDocumentAI()

from ..core.config import settings


def process_document_bytes(content: bytes, mime_type: str = "application/pdf") -> Optional[object]:
    """Process a document with Google Document AI, returning the Document object.

    Requires GOOGLE_APPLICATION_CREDENTIALS and DOC_AI_PROCESSOR_ID to be set.
    Returns None if not configured.
    """
    if not (settings.google_application_credentials and settings.doc_ai_processor_id):
        return None
    # The client reads credentials from GOOGLE_APPLICATION_CREDENTIALS
    os.environ.setdefault("GOOGLE_APPLICATION_CREDENTIALS", settings.google_application_credentials)

    client = documentai.DocumentProcessorServiceClient()
    name = client.processor_path(*_parse_processor_path(settings.doc_ai_processor_id))
    raw_document = documentai.RawDocument(content=content, mime_type=mime_type)
    request = documentai.ProcessRequest(name=name, raw_document=raw_document)
    result = client.process_document(request=request)
    return result.document


def extract_text_blocks(doc) -> List[str]:
    if not doc:
        return []
    out: List[str] = []
    # Extract paragraphs text as blocks
    for page in doc.pages:
        for para in page.paragraphs:
            out.append(_layout_to_text(para.layout, doc))
    if not out and doc.text:
        out.append(doc.text)
    return out


def _layout_to_text(layout, doc) -> str:
    if not layout.text_anchor:
        return ""
    txt = []
    for seg in layout.text_anchor.text_segments:
        start = int(seg.start_index or 0)
        end = int(seg.end_index or 0)
        txt.append(doc.text[start:end])
    return "".join(txt).strip()


def _parse_processor_path(path: str):
    # Expected: projects/{project}/locations/{location}/processors/{processor}
    parts = path.split("/")
    project = parts[1]
    location = parts[3]
    processor = parts[5]
    return project, location, processor


