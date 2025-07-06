# backend/app/services/content_filter.py
"""Content filtering service for sensitive data in retrieved content."""

import logging
from typing import List, Dict, Any, Optional
from app.chat.secret_scanner import secret_scanner

logger = logging.getLogger(__name__)


class ContentFilter:
    """Service for filtering sensitive content from retrieved chunks."""
    
    def __init__(self):
        self.scanner = secret_scanner
        
    def filter_chunk(self, chunk: Dict[str, Any]) -> Dict[str, Any]:
        """Filter a single chunk for sensitive content."""
        content = chunk.get("content", "")
        if not content:
            return chunk
            
        # Scan for secrets
        findings = self.scanner.scan(content)
        
        if findings:
            # Redact secrets from content
            filtered_content = self.scanner.redact(content, findings)
            
            # Create a copy of the chunk with filtered content
            filtered_chunk = chunk.copy()
            filtered_chunk["content"] = filtered_content
            
            # Add metadata about filtering
            metadata = filtered_chunk.get("metadata", {})
            metadata["content_filtered"] = True
            metadata["redacted_secrets"] = len(findings)
            metadata["redaction_summary"] = self.scanner.get_redaction_summary(findings)
            filtered_chunk["metadata"] = metadata
            
            logger.info(
                f"Filtered {len(findings)} secrets from chunk in {metadata.get('file_path', 'unknown file')}"
            )
            
            return filtered_chunk
        
        return chunk
    
    def filter_chunks(self, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter a list of chunks for sensitive content."""
        filtered_chunks = []
        
        for chunk in chunks:
            filtered_chunk = self.filter_chunk(chunk)
            filtered_chunks.append(filtered_chunk)
            
        return filtered_chunks
    
    def should_exclude_chunk(self, chunk: Dict[str, Any], strict_mode: bool = False) -> bool:
        """Determine if a chunk should be completely excluded due to sensitive content."""
        content = chunk.get("content", "")
        if not content:
            return False
            
        findings = self.scanner.scan(content)
        
        if not findings:
            return False
            
        # In strict mode, exclude chunks with any high-severity secrets
        if strict_mode:
            high_severity_count = sum(1 for f in findings if f.get("severity") == "high")
            return high_severity_count > 0
        
        # In normal mode, exclude only if the chunk is mostly secrets
        # (e.g., more than 50% of content would be redacted)
        total_redacted_length = sum(f["end"] - f["start"] for f in findings)
        redaction_ratio = total_redacted_length / len(content)
        
        return redaction_ratio > 0.5
    
    def filter_and_validate_chunks(
        self, 
        chunks: List[Dict[str, Any]], 
        strict_mode: bool = False
    ) -> tuple[List[Dict[str, Any]], List[str]]:
        """Filter chunks and return both filtered chunks and warnings."""
        filtered_chunks = []
        warnings = []
        excluded_count = 0
        
        for chunk in chunks:
            # Check if chunk should be excluded entirely
            if self.should_exclude_chunk(chunk, strict_mode):
                excluded_count += 1
                file_path = chunk.get("metadata", {}).get("file_path", "unknown")
                warnings.append(f"Excluded chunk from {file_path} due to sensitive content")
                continue
                
            # Filter the chunk
            filtered_chunk = self.filter_chunk(chunk)
            
            # Check if any content was redacted
            if filtered_chunk.get("metadata", {}).get("content_filtered"):
                redaction_summary = filtered_chunk["metadata"]["redaction_summary"]
                warnings.append(f"Redacted content: {redaction_summary}")
                
            filtered_chunks.append(filtered_chunk)
        
        if excluded_count > 0:
            warnings.append(f"Excluded {excluded_count} chunks due to sensitive content")
            
        return filtered_chunks, warnings
    
    def is_content_safe(self, content: str) -> tuple[bool, List[str]]:
        """Check if content is safe to include in context."""
        findings = self.scanner.scan(content)
        
        if not findings:
            return True, []
        
        # Categorize findings
        high_severity = [f for f in findings if f.get("severity") == "high"]
        medium_severity = [f for f in findings if f.get("severity") == "medium"]
        
        warnings = []
        
        if high_severity:
            warnings.append(f"Found {len(high_severity)} high-severity secrets")
            
        if medium_severity:
            warnings.append(f"Found {len(medium_severity)} medium-severity secrets")
            
        # Content is unsafe if it has high-severity secrets
        is_safe = len(high_severity) == 0
        
        return is_safe, warnings
    
    def get_safe_preview(self, content: str, max_length: int = 200) -> str:
        """Get a safe preview of content with secrets redacted."""
        findings = self.scanner.scan(content)
        
        if findings:
            redacted_content = self.scanner.redact(content, findings)
        else:
            redacted_content = content
            
        # Truncate to max length
        if len(redacted_content) > max_length:
            return redacted_content[:max_length] + "..."
        
        return redacted_content


# Global content filter instance
content_filter = ContentFilter()