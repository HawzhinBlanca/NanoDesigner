from __future__ import annotations

import io
from typing import List, Dict, Any
from pathlib import Path

try:
    from unstructured.partition.auto import partition
    from unstructured.partition.pdf import partition_pdf
    from unstructured.partition.html import partition_html
    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False


def basic_parse_text_blobs(urls: List[str]) -> List[str]:
    """Extract text descriptions from URLs without fetching remote content."""
    results = []
    for url in urls:
        if not isinstance(url, str) or not url:
            continue
        
        # Parse URL to extract meaningful context
        path = Path(url)
        filename = path.name
        
        # Generate descriptive text based on URL/filename
        if filename:
            # Extract file type and name
            ext = path.suffix.lower()
            name_parts = path.stem.replace('_', ' ').replace('-', ' ')
            
            # Build description
            if ext in ['.pdf', '.doc', '.docx']:
                results.append(f"Document: {name_parts}")
            elif ext in ['.png', '.jpg', '.jpeg', '.gif', '.webp']:
                results.append(f"Image asset: {name_parts}")
            elif ext in ['.svg']:
                results.append(f"Vector graphic: {name_parts}")
            elif 'brand' in url.lower() or 'guideline' in url.lower():
                results.append(f"Brand guideline reference: {name_parts}")
            elif 'logo' in url.lower():
                results.append(f"Logo asset: {name_parts}")
            else:
                results.append(f"Asset: {name_parts}")
        else:
            # Generic reference
            results.append(f"Reference: {url}")
    
    return results if results else ["No parseable content"]


def process_document_bytes(
    content: bytes,
    mime_type: str = "application/pdf"
) -> Dict[str, Any]:
    """
    Process document bytes using Unstructured library if available.
    
    Args:
        content: Document bytes
        mime_type: MIME type of document
        
    Returns:
        Dictionary with extracted text and metadata
    """
    if not UNSTRUCTURED_AVAILABLE:
        # Fallback to basic text extraction
        return {
            "text": content.decode("utf-8", errors="ignore"),
            "elements": [],
            "metadata": {"mime_type": mime_type}
        }
    
    try:
        # Create file-like object
        file_obj = io.BytesIO(content)
        
        # Choose appropriate partition function
        if mime_type == "application/pdf":
            elements = partition_pdf(file=file_obj, strategy="auto")
        elif mime_type == "text/html":
            elements = partition_html(file=file_obj)
        else:
            elements = partition(file=file_obj)
        
        # Extract text from elements
        text_parts = []
        element_list = []
        
        for element in elements:
            text = str(element)
            text_parts.append(text)
            element_list.append({
                "type": element.__class__.__name__,
                "text": text
            })
        
        return {
            "text": "\n\n".join(text_parts),
            "elements": element_list,
            "metadata": {"mime_type": mime_type}
        }
        
    except Exception as e:
        # Fallback on error
        return {
            "text": content.decode("utf-8", errors="ignore"),
            "elements": [],
            "metadata": {"mime_type": mime_type, "error": str(e)}
        }


