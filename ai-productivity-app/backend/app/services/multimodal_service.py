"""Multi-modal document support for images, diagrams, and other media."""

import asyncio
import base64
import io
import logging
import mimetypes
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Union
import hashlib

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    logger.warning("PIL not available - image processing will be limited")

from sqlalchemy.orm import Session
from app.models.code_document import CodeDocument
from app.services.embedding_service import embedding_service
from app.llm.client import llm_client
from app.core.config import settings

logger = logging.getLogger(__name__)


class MultiModalProcessor:
    """Process various types of media files for knowledge extraction."""
    
    def __init__(self):
        self.supported_image_types = {'.png', '.jpg', '.jpeg', '.gif', '.bmp', '.tiff', '.webp'}
        self.supported_diagram_types = {'.svg', '.drawio', '.mermaid', '.puml', '.plantuml'}
        self.supported_document_types = {'.pdf', '.docx', '.pptx', '.xlsx'}
        self.max_image_size = (1920, 1080)  # Max resolution for processing
        self.max_file_size = 10 * 1024 * 1024  # 10MB limit
    
    async def process_file(self, 
                          file_path: str, 
                          content: bytes, 
                          mime_type: Optional[str] = None) -> Dict[str, Any]:
        """Process a multi-modal file and extract knowledge."""
        if not mime_type:
            mime_type, _ = mimetypes.guess_type(file_path)
        
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext in self.supported_image_types:
                return await self._process_image(file_path, content, mime_type)
            elif file_ext in self.supported_diagram_types:
                return await self._process_diagram(file_path, content, mime_type)
            elif file_ext in self.supported_document_types:
                return await self._process_document(file_path, content, mime_type)
            else:
                return await self._process_generic_file(file_path, content, mime_type)
        
        except Exception as e:
            logger.error(f"Failed to process file {file_path}: {e}")
            return {
                "success": False,
                "error": str(e),
                "extracted_text": "",
                "metadata": {"file_path": file_path, "mime_type": mime_type}
            }
    
    async def _process_image(self, 
                           file_path: str, 
                           content: bytes, 
                           mime_type: str) -> Dict[str, Any]:
        """Process image files using vision models."""
        if not PIL_AVAILABLE:
            return self._create_fallback_result(file_path, "Image processing unavailable")
        
        try:
            # Load and analyze image
            image = Image.open(io.BytesIO(content))
            image_info = self._analyze_image(image)
            
            # Extract text using vision model if available
            extracted_text = await self._extract_text_from_image(content, file_path)
            
            # Generate description using vision model
            description = await self._describe_image(content, file_path)
            
            # Create searchable content
            searchable_content = self._create_image_searchable_content(
                file_path, description, extracted_text, image_info
            )
            
            return {
                "success": True,
                "content_type": "image",
                "extracted_text": searchable_content,
                "metadata": {
                    "file_path": file_path,
                    "mime_type": mime_type,
                    "image_info": image_info,
                    "description": description,
                    "ocr_text": extracted_text,
                    "processing_method": "vision_model"
                }
            }
        
        except Exception as e:
            logger.error(f"Image processing failed for {file_path}: {e}")
            return self._create_fallback_result(file_path, f"Image processing error: {e}")
    
    async def _process_diagram(self, 
                             file_path: str, 
                             content: bytes, 
                             mime_type: str) -> Dict[str, Any]:
        """Process diagram files (SVG, PlantUML, Mermaid, etc.)."""
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext == '.svg':
                return await self._process_svg(file_path, content)
            elif file_ext in {'.mermaid', '.mmd'}:
                return await self._process_mermaid(file_path, content)
            elif file_ext in {'.puml', '.plantuml'}:
                return await self._process_plantuml(file_path, content)
            elif file_ext == '.drawio':
                return await self._process_drawio(file_path, content)
            else:
                return self._create_fallback_result(file_path, "Unsupported diagram format")
        
        except Exception as e:
            logger.error(f"Diagram processing failed for {file_path}: {e}")
            return self._create_fallback_result(file_path, f"Diagram processing error: {e}")
    
    async def _process_svg(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """Process SVG diagrams."""
        try:
            svg_text = content.decode('utf-8')
            
            # Extract text content from SVG
            import re
            text_pattern = r'<text[^>]*>(.*?)</text>'
            title_pattern = r'<title[^>]*>(.*?)</title>'
            desc_pattern = r'<desc[^>]*>(.*?)</desc>'
            
            text_elements = re.findall(text_pattern, svg_text, re.DOTALL | re.IGNORECASE)
            titles = re.findall(title_pattern, svg_text, re.DOTALL | re.IGNORECASE)
            descriptions = re.findall(desc_pattern, svg_text, re.DOTALL | re.IGNORECASE)
            
            # Combine extracted text
            extracted_text = ' '.join([
                *titles,
                *descriptions,
                *[text.strip() for text in text_elements if text.strip()]
            ])
            
            # Analyze SVG structure
            structure_info = self._analyze_svg_structure(svg_text)
            
            # Generate comprehensive description
            diagram_description = await self._describe_diagram(
                svg_text, "SVG diagram", structure_info
            )
            
            searchable_content = f"""
SVG Diagram: {file_path}

Description: {diagram_description}

Text Content: {extracted_text}

Structure: {structure_info['summary']}

Elements: {', '.join(structure_info['elements'])}
"""
            
            return {
                "success": True,
                "content_type": "diagram",
                "extracted_text": searchable_content.strip(),
                "metadata": {
                    "file_path": file_path,
                    "diagram_type": "svg",
                    "structure_info": structure_info,
                    "description": diagram_description,
                    "text_elements": text_elements,
                    "processing_method": "svg_parser"
                }
            }
        
        except Exception as e:
            logger.error(f"SVG processing failed: {e}")
            return self._create_fallback_result(file_path, f"SVG processing error: {e}")
    
    async def _process_mermaid(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """Process Mermaid diagrams."""
        try:
            mermaid_text = content.decode('utf-8')
            
            # Parse Mermaid syntax
            diagram_info = self._parse_mermaid_syntax(mermaid_text)
            
            # Generate description
            description = await self._describe_diagram(
                mermaid_text, "Mermaid diagram", diagram_info
            )
            
            searchable_content = f"""
Mermaid Diagram: {file_path}

Type: {diagram_info['type']}
Description: {description}

Content:
{mermaid_text}

Nodes: {', '.join(diagram_info.get('nodes', []))}
Relationships: {len(diagram_info.get('edges', []))} connections
"""
            
            return {
                "success": True,
                "content_type": "diagram",
                "extracted_text": searchable_content.strip(),
                "metadata": {
                    "file_path": file_path,
                    "diagram_type": "mermaid",
                    "diagram_info": diagram_info,
                    "description": description,
                    "processing_method": "mermaid_parser"
                }
            }
        
        except Exception as e:
            logger.error(f"Mermaid processing failed: {e}")
            return self._create_fallback_result(file_path, f"Mermaid processing error: {e}")
    
    async def _process_plantuml(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """Process PlantUML diagrams."""
        try:
            plantuml_text = content.decode('utf-8')
            
            # Parse PlantUML syntax
            diagram_info = self._parse_plantuml_syntax(plantuml_text)
            
            # Generate description
            description = await self._describe_diagram(
                plantuml_text, "PlantUML diagram", diagram_info
            )
            
            searchable_content = f"""
PlantUML Diagram: {file_path}

Type: {diagram_info['type']}
Description: {description}

Content:
{plantuml_text}

Components: {', '.join(diagram_info.get('components', []))}
Relationships: {len(diagram_info.get('relationships', []))} connections
"""
            
            return {
                "success": True,
                "content_type": "diagram",
                "extracted_text": searchable_content.strip(),
                "metadata": {
                    "file_path": file_path,
                    "diagram_type": "plantuml",
                    "diagram_info": diagram_info,
                    "description": description,
                    "processing_method": "plantuml_parser"
                }
            }
        
        except Exception as e:
            logger.error(f"PlantUML processing failed: {e}")
            return self._create_fallback_result(file_path, f"PlantUML processing error: {e}")
    
    async def _process_drawio(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """Process Draw.io diagrams."""
        try:
            # Draw.io files are XML-based
            import xml.etree.ElementTree as ET
            
            drawio_text = content.decode('utf-8')
            root = ET.fromstring(drawio_text)
            
            # Extract text from draw.io elements
            text_elements = []
            for elem in root.iter():
                if elem.text and elem.text.strip():
                    text_elements.append(elem.text.strip())
            
            # Analyze structure
            structure_info = {
                "total_elements": len(list(root.iter())),
                "text_elements": len(text_elements),
                "pages": len(root.findall(".//diagram"))
            }
            
            # Generate description
            description = await self._describe_diagram(
                drawio_text, "Draw.io diagram", structure_info
            )
            
            searchable_content = f"""
Draw.io Diagram: {file_path}

Description: {description}

Text Elements: {' | '.join(text_elements)}

Structure: {structure_info['total_elements']} total elements, {structure_info['pages']} pages
"""
            
            return {
                "success": True,
                "content_type": "diagram",
                "extracted_text": searchable_content.strip(),
                "metadata": {
                    "file_path": file_path,
                    "diagram_type": "drawio",
                    "structure_info": structure_info,
                    "description": description,
                    "text_elements": text_elements,
                    "processing_method": "xml_parser"
                }
            }
        
        except Exception as e:
            logger.error(f"Draw.io processing failed: {e}")
            return self._create_fallback_result(file_path, f"Draw.io processing error: {e}")
    
    async def _process_document(self, 
                              file_path: str, 
                              content: bytes, 
                              mime_type: str) -> Dict[str, Any]:
        """Process document files (PDF, Word, etc.)."""
        file_ext = Path(file_path).suffix.lower()
        
        try:
            if file_ext == '.pdf':
                return await self._process_pdf(file_path, content)
            elif file_ext == '.docx':
                return await self._process_docx(file_path, content)
            else:
                # For unsupported document types, extract basic metadata
                searchable_content = f"""
Document: {file_path}
Type: {mime_type or 'unknown document'}
Size: {len(content)} bytes

This document type is not fully supported for text extraction.
File extension: {file_ext}
"""
                return {
                    "success": True,
                    "content_type": "document",
                    "extracted_text": searchable_content.strip(),
                    "metadata": {
                        "file_path": file_path,
                        "mime_type": mime_type,
                        "file_size": len(content),
                        "processing_method": "metadata_only"
                    }
                }
        
        except Exception as e:
            logger.error(f"Document processing failed for {file_path}: {e}")
            return self._create_fallback_result(file_path, f"Document processing error: {e}")
    
    async def _process_pdf(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """Process PDF documents with text extraction."""
        try:
            # Try to extract text using basic text extraction
            # In a production environment, you'd use libraries like PyPDF2, pdfplumber, or pymupdf
            
            # For now, we'll simulate PDF text extraction
            # This would be replaced with actual PDF processing
            
            # Check if it's a text-based PDF by looking for common PDF markers
            content_str = content.decode('latin-1', errors='ignore')  # PDFs use latin-1 encoding
            
            # Extract basic metadata from PDF structure
            title_match = re.search(r'/Title\s*\(([^)]+)\)', content_str)
            author_match = re.search(r'/Author\s*\(([^)]+)\)', content_str)
            
            title = title_match.group(1) if title_match else Path(file_path).stem
            author = author_match.group(1) if author_match else "Unknown"
            
            # Simple text extraction by looking for readable text patterns
            # This is a basic approximation - real implementation would use proper PDF libraries
            text_content = ""
            
            # Look for text objects in PDF
            text_objects = re.findall(r'BT\s+.*?ET', content_str, re.DOTALL)
            for obj in text_objects[:10]:  # Limit to first 10 text objects
                # Extract text between parentheses (simplified)
                texts = re.findall(r'\(([^)]+)\)', obj)
                text_content += " ".join(texts) + " "
            
            # If no text found, indicate it might be image-based
            if not text_content.strip():
                text_content = f"PDF document '{title}' - text extraction may require OCR for image-based content."
            
            searchable_content = f"""
PDF Document: {file_path}
Title: {title}
Author: {author}
Size: {len(content)} bytes

Content:
{text_content[:2000]}...

This is a PDF document that may contain additional text, images, or formatted content.
"""
            
            return {
                "success": True,
                "content_type": "document",
                "extracted_text": searchable_content.strip(),
                "metadata": {
                    "file_path": file_path,
                    "document_type": "pdf",
                    "title": title,
                    "author": author,
                    "file_size": len(content),
                    "processing_method": "basic_pdf_extraction"
                }
            }
            
        except Exception as e:
            logger.error(f"PDF processing failed: {e}")
            return self._create_fallback_result(file_path, f"PDF processing error: {e}")
    
    async def _process_docx(self, file_path: str, content: bytes) -> Dict[str, Any]:
        """Process Word documents with text extraction."""
        try:
            # Word documents are actually ZIP files containing XML
            import zipfile
            import xml.etree.ElementTree as ET
            
            # Extract text from DOCX
            text_content = ""
            metadata = {"file_path": file_path, "document_type": "docx"}
            
            with zipfile.ZipFile(io.BytesIO(content), 'r') as docx_zip:
                # Read document.xml which contains the main text
                try:
                    doc_xml = docx_zip.read('word/document.xml')
                    root = ET.fromstring(doc_xml)
                    
                    # Extract all text elements
                    # Word XML uses namespaces, so we look for text elements
                    for elem in root.iter():
                        if elem.tag.endswith('}t'):  # Text elements end with }t
                            if elem.text:
                                text_content += elem.text + " "
                
                except KeyError:
                    # If document.xml not found, try to extract any readable content
                    text_content = "DOCX structure detected but text extraction failed."
                
                # Try to extract metadata from core.xml
                try:
                    core_xml = docx_zip.read('docProps/core.xml')
                    core_root = ET.fromstring(core_xml)
                    
                    for elem in core_root.iter():
                        if elem.tag.endswith('}title') and elem.text:
                            metadata["title"] = elem.text
                        elif elem.tag.endswith('}creator') and elem.text:
                            metadata["author"] = elem.text
                        elif elem.tag.endswith('}description') and elem.text:
                            metadata["description"] = elem.text
                
                except KeyError:
                    pass  # Metadata extraction is optional
            
            if not text_content.strip():
                text_content = "Word document detected but text content could not be extracted."
            
            searchable_content = f"""
Word Document: {file_path}
Title: {metadata.get('title', Path(file_path).stem)}
Author: {metadata.get('author', 'Unknown')}
Size: {len(content)} bytes

Content:
{text_content[:2000]}...

This is a Microsoft Word document.
"""
            
            metadata.update({
                "file_size": len(content),
                "processing_method": "docx_xml_extraction"
            })
            
            return {
                "success": True,
                "content_type": "document",
                "extracted_text": searchable_content.strip(),
                "metadata": metadata
            }
            
        except Exception as e:
            logger.error(f"DOCX processing failed: {e}")
            return self._create_fallback_result(file_path, f"DOCX processing error: {e}")
    
    async def _process_generic_file(self, 
                                   file_path: str, 
                                   content: bytes, 
                                   mime_type: str) -> Dict[str, Any]:
        """Process unsupported file types with basic metadata extraction."""
        try:
            # Try to decode as text
            try:
                text_content = content.decode('utf-8')
                if len(text_content.strip()) > 0:
                    return {
                        "success": True,
                        "content_type": "text",
                        "extracted_text": text_content,
                        "metadata": {
                            "file_path": file_path,
                            "mime_type": mime_type,
                            "processing_method": "text_decode"
                        }
                    }
            except UnicodeDecodeError:
                pass
            
            # Fallback to binary analysis
            file_info = {
                "size": len(content),
                "hash": hashlib.md5(content).hexdigest(),
                "is_binary": True
            }
            
            searchable_content = f"""
File: {file_path}
Type: {mime_type or 'unknown'}
Size: {file_info['size']} bytes
Hash: {file_info['hash']}

This is a binary file that cannot be processed for text content.
"""
            
            return {
                "success": True,
                "content_type": "binary",
                "extracted_text": searchable_content.strip(),
                "metadata": {
                    "file_path": file_path,
                    "mime_type": mime_type,
                    "file_info": file_info,
                    "processing_method": "binary_analysis"
                }
            }
        
        except Exception as e:
            return self._create_fallback_result(file_path, f"Generic processing error: {e}")
    
    def _analyze_image(self, image: Image.Image) -> Dict[str, Any]:
        """Analyze image properties."""
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image.format,
            "has_transparency": image.mode in ('RGBA', 'LA'),
            "aspect_ratio": round(image.width / image.height, 2),
            "megapixels": round((image.width * image.height) / 1000000, 2)
        }
    
    def _analyze_svg_structure(self, svg_text: str) -> Dict[str, Any]:
        """Analyze SVG structure and elements."""
        import re
        
        # Count different element types
        elements = re.findall(r'<(\w+)[^>]*>', svg_text)
        element_counts = {}
        for element in elements:
            element_counts[element] = element_counts.get(element, 0) + 1
        
        # Look for common diagram patterns
        has_arrows = bool(re.search(r'marker|arrow', svg_text, re.IGNORECASE))
        has_shapes = any(shape in elements for shape in ['rect', 'circle', 'ellipse', 'polygon'])
        has_paths = 'path' in elements
        
        return {
            "elements": list(element_counts.keys()),
            "element_counts": element_counts,
            "has_arrows": has_arrows,
            "has_shapes": has_shapes,
            "has_paths": has_paths,
            "total_elements": len(elements),
            "summary": f"SVG with {len(elements)} elements including {', '.join(list(element_counts.keys())[:5])}"
        }
    
    def _parse_mermaid_syntax(self, mermaid_text: str) -> Dict[str, Any]:
        """Parse Mermaid diagram syntax."""
        lines = [line.strip() for line in mermaid_text.split('\n') if line.strip()]
        
        # Determine diagram type
        diagram_type = "unknown"
        if any(line.startswith(('graph', 'flowchart')) for line in lines):
            diagram_type = "flowchart"
        elif any(line.startswith('sequenceDiagram') for line in lines):
            diagram_type = "sequence"
        elif any(line.startswith('classDiagram') for line in lines):
            diagram_type = "class"
        elif any(line.startswith('erDiagram') for line in lines):
            diagram_type = "entity_relationship"
        
        # Extract nodes and edges (simplified)
        nodes = set()
        edges = []
        
        for line in lines:
            # Simple node/edge extraction
            if '-->' in line or '---' in line:
                parts = line.split('--')
                if len(parts) >= 2:
                    nodes.add(parts[0].strip())
                    nodes.add(parts[-1].strip())
                    edges.append(line)
        
        return {
            "type": diagram_type,
            "nodes": list(nodes),
            "edges": edges,
            "total_lines": len(lines)
        }
    
    def _parse_plantuml_syntax(self, plantuml_text: str) -> Dict[str, Any]:
        """Parse PlantUML diagram syntax."""
        lines = [line.strip() for line in plantuml_text.split('\n') if line.strip()]
        
        # Determine diagram type
        diagram_type = "unknown"
        if any('@startuml' in line for line in lines):
            if any('class' in line for line in lines):
                diagram_type = "class"
            elif any('actor' in line or 'participant' in line for line in lines):
                diagram_type = "sequence"
            elif any('component' in line for line in lines):
                diagram_type = "component"
            else:
                diagram_type = "uml"
        
        # Extract components and relationships
        components = set()
        relationships = []
        
        for line in lines:
            # Look for relationship arrows
            if any(arrow in line for arrow in ['-->', '<--', '->', '<-', '--', '..']):
                relationships.append(line)
                # Extract component names (simplified)
                parts = line.split()
                if len(parts) >= 3:
                    components.add(parts[0])
                    components.add(parts[-1])
        
        return {
            "type": diagram_type,
            "components": list(components),
            "relationships": relationships,
            "total_lines": len(lines)
        }
    
    async def _extract_text_from_image(self, content: bytes, file_path: str) -> str:
        """Extract text from image using OCR or vision models."""
        try:
            # Basic text extraction attempt
            # In production, this would use Tesseract OCR, Google Vision API, or similar
            
            # For now, we'll look for any embedded text in image metadata
            # and provide a meaningful fallback
            
            if PIL_AVAILABLE:
                try:
                    image = Image.open(io.BytesIO(content))
                    
                    # Check EXIF data for any text information
                    exif_data = {}
                    if hasattr(image, '_getexif') and image._getexif():
                        exif_data = image._getexif()
                    
                    # Look for common text fields in EXIF
                    text_fields = []
                    for tag_id in [270, 271, 272]:  # ImageDescription, Make, Model
                        if tag_id in exif_data:
                            text_fields.append(str(exif_data[tag_id]))
                    
                    if text_fields:
                        return " ".join(text_fields)
                    
                except Exception:
                    pass  # Continue to fallback
            
            # Fallback: analyze filename for text content
            filename = Path(file_path).stem
            
            # If filename contains meaningful text, use it
            if len(filename) > 3 and not filename.isdigit():
                # Convert camelCase and snake_case to readable text
                readable_name = re.sub(r'([a-z])([A-Z])', r'\1 \2', filename)
                readable_name = readable_name.replace('_', ' ').replace('-', ' ')
                return f"Image filename suggests content: {readable_name}"
            
            return ""  # No text found
            
        except Exception as e:
            logger.error(f"Text extraction from image failed: {e}")
            return ""
    
    async def _describe_image(self, content: bytes, file_path: str) -> str:
        """Generate description of image using vision models."""
        try:
            # Analyze image properties for description
            if PIL_AVAILABLE:
                try:
                    image = Image.open(io.BytesIO(content))
                    width, height = image.size
                    mode = image.mode
                    format_name = image.format or "Unknown"
                    
                    # Determine image characteristics
                    aspect_ratio = width / height
                    megapixels = (width * height) / 1000000
                    
                    # Analyze image content based on properties
                    description_parts = [f"{format_name} image"]
                    
                    if aspect_ratio > 2:
                        description_parts.append("wide banner or panoramic format")
                    elif aspect_ratio < 0.5:
                        description_parts.append("tall or portrait format")
                    else:
                        description_parts.append("standard rectangular format")
                    
                    if megapixels > 10:
                        description_parts.append("high resolution")
                    elif megapixels < 0.5:
                        description_parts.append("low resolution or thumbnail")
                    
                    # Analyze filename for context
                    filename = Path(file_path).stem.lower()
                    
                    if any(word in filename for word in ['diagram', 'chart', 'graph', 'plot']):
                        description_parts.append("likely contains charts or diagrams")
                    elif any(word in filename for word in ['screenshot', 'screen', 'ui', 'interface']):
                        description_parts.append("appears to be a user interface screenshot")
                    elif any(word in filename for word in ['logo', 'icon', 'button']):
                        description_parts.append("appears to be a logo or icon")
                    elif any(word in filename for word in ['architecture', 'flow', 'design']):
                        description_parts.append("likely shows system architecture or design")
                    
                    # Color analysis
                    if mode == 'L':
                        description_parts.append("grayscale image")
                    elif mode == 'RGBA':
                        description_parts.append("with transparency")
                    
                    return f"{Path(file_path).name}: {', '.join(description_parts)} ({width}x{height} pixels)"
                    
                except Exception as e:
                    logger.debug(f"PIL analysis failed: {e}")
            
            # Fallback description based on filename analysis
            filename = Path(file_path).stem.lower()
            file_ext = Path(file_path).suffix.lower()
            
            if file_ext in ['.png', '.jpg', '.jpeg']:
                base_desc = "Digital image"
            elif file_ext in ['.svg']:
                base_desc = "Vector graphic"
            elif file_ext in ['.gif']:
                base_desc = "Animated image"
            else:
                base_desc = "Image file"
            
            # Enhanced filename analysis
            context_clues = []
            if 'api' in filename:
                context_clues.append("API-related")
            if any(word in filename for word in ['test', 'spec', 'example']):
                context_clues.append("test or example content")
            if any(word in filename for word in ['error', 'exception', 'fail']):
                context_clues.append("error or failure documentation")
            if any(word in filename for word in ['flow', 'process', 'workflow']):
                context_clues.append("process or workflow diagram")
            
            if context_clues:
                return f"{base_desc}: {Path(file_path).name} - {', '.join(context_clues)}"
            else:
                return f"{base_desc}: {Path(file_path).name}"
            
        except Exception as e:
            logger.error(f"Image description failed: {e}")
            return f"Image: {Path(file_path).name}"
    
    async def _describe_diagram(self, 
                               content: str, 
                               diagram_type: str, 
                               structure_info: Dict[str, Any]) -> str:
        """Generate description of diagram using LLM."""
        try:
            prompt = f"""Analyze this {diagram_type} and provide a brief description:

Content:
{content[:1000]}...

Structure: {structure_info}

Provide a 2-3 sentence description of what this diagram shows and its purpose."""
            
            response = await llm_client.complete(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=150,
                temperature=0.3
            )
            
            if hasattr(response, 'choices') and response.choices:
                return response.choices[0].message.content.strip()
            elif hasattr(response, 'output') and response.output:
                return response.output[0].content.strip()
            
        except Exception as e:
            logger.error(f"Diagram description failed: {e}")
        
        return f"{diagram_type} with {structure_info.get('total_elements', 'unknown')} elements"
    
    def _create_image_searchable_content(self, 
                                       file_path: str,
                                       description: str,
                                       ocr_text: str,
                                       image_info: Dict[str, Any]) -> str:
        """Create searchable content for images."""
        return f"""
Image: {file_path}

Description: {description}

Extracted Text: {ocr_text}

Properties: {image_info['width']}x{image_info['height']} pixels, {image_info['format']} format

Type: Visual content, {image_info.get('megapixels', 0)}MP image
""".strip()
    
    def _create_fallback_result(self, file_path: str, error_msg: str) -> Dict[str, Any]:
        """Create fallback result for failed processing."""
        return {
            "success": False,
            "content_type": "unknown",
            "extracted_text": f"File: {file_path}\nProcessing failed: {error_msg}",
            "metadata": {
                "file_path": file_path,
                "error": error_msg,
                "processing_method": "fallback"
            }
        }


# Global instance
multimodal_processor = MultiModalProcessor()