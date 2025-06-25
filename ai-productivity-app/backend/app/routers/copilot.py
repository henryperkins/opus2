"""
Code completion endpoint for Monacopilot integration.
Provides AI-powered code suggestions via OpenAI/Azure OpenAI.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Dict, List, Optional, Any
import logging

from ..database import get_db
from ..dependencies import get_current_user
from ..models.user import User
from ..llm.client import llm_client
from ..auth.security import limiter

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/code", tags=["copilot"])


class CompletionMetadata(BaseModel):
    """Metadata from Monacopilot completion request"""
    language: str
    cursorPosition: Dict[str, int]
    filename: Optional[str] = None
    technologies: Optional[List[str]] = None
    textBeforeCursor: str
    textAfterCursor: str
    editorState: Dict[str, str]


class CompletionRequest(BaseModel):
    """Request payload for code completion"""
    completionMetadata: CompletionMetadata
    additionalContext: Optional[Dict[str, Any]] = Field(default_factory=dict)


class CompletionResponse(BaseModel):
    """Response payload for code completion"""
    completion: Optional[str] = None
    error: Optional[str] = None


@router.post("/copilot", response_model=CompletionResponse)
@limiter.limit("30/minute")  # 30 requests per minute per user
async def complete_code(
    request: Request,
    completion_request: CompletionRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Generate code completion suggestions using AI.
    
    This endpoint receives completion requests from Monacopilot and returns
    AI-generated code suggestions based on the current context.
    """
    try:
        metadata = completion_request.completionMetadata
        
        # Log request for monitoring and cost tracking
        logger.info(
            f"Code completion request from user {current_user.id}: "
            f"language={metadata.language}, "
            f"cursor_line={metadata.cursorPosition.get('lineNumber', 0)}, "
            f"context_length={len(metadata.textBeforeCursor + metadata.textAfterCursor)}"
        )
        
        # Build context-aware prompt
        prompt = build_completion_prompt(metadata)
        
        # Ensure the LLM client is configured properly for the current runtime settings
        # Validate that we're using a supported deployment name for Azure
        await llm_client.reconfigure()
        
        # Build completion messages
        messages = [
            {"role": "system", "content": prompt.split("\n\nUser:")[0].replace("System: ", "")},
            {"role": "user", "content": prompt.split("\n\nUser:")[1].split("\n\nAssistant:")[0] if "\n\nUser:" in prompt else prompt}
        ]
        
        try:
            response = await llm_client.complete(
                messages=messages,
                max_tokens=200,  # Limit for code completions
                temperature=0.2,  # Lower temperature for more deterministic code
            )
            
            # Extract completion text from response
            if hasattr(response, 'choices') and response.choices:
                completion_text = response.choices[0].message.content or ""
            elif hasattr(response, 'output_text'):
                completion_text = response.output_text or ""
            elif hasattr(response, 'output'):
                completion_text = response.output or ""
            else:
                completion_text = str(response).strip()
            
            # Clean up completion (remove any markdown artifacts)
            completion_text = clean_completion(completion_text)
            
            logger.info(f"Generated completion for user {current_user.id}: {len(completion_text)} chars")
            
            return CompletionResponse(completion=completion_text)
            
        except Exception as llm_error:
            logger.error(f"LLM completion error for user {current_user.id}: {llm_error}")
            return CompletionResponse(
                completion=None,
                error="AI service temporarily unavailable"
            )
            
    except Exception as e:
        logger.error(f"Code completion error for user {current_user.id}: {e}")
        return CompletionResponse(
            completion=None,
            error="Code completion failed"
        )


def build_completion_prompt(metadata: CompletionMetadata) -> str:
    """Build a context-aware prompt for code completion"""
    
    language = metadata.language
    before_cursor = metadata.textBeforeCursor
    after_cursor = metadata.textAfterCursor
    filename = metadata.filename or f"file.{get_file_extension(language)}"
    technologies = metadata.technologies or []
    
    # Determine completion mode based on context
    completion_mode = metadata.editorState.get("completionMode", "continue")
    
    # Build technology context
    tech_context = ""
    if technologies:
        tech_context = f"This is a {', '.join(technologies)} project. "
    
    # Build the prompt based on completion mode
    if completion_mode == "insert":
        system_prompt = (
            f"You are an AI coding assistant specializing in {language}. "
            f"{tech_context}"
            f"Complete the code at the cursor position. "
            f"Return only the code that should be inserted, without explanations or markdown."
        )
        
        user_prompt = f"""File: {filename}

Code before cursor:
{before_cursor}

Code after cursor:
{after_cursor}

Complete the code at the cursor position:"""
        
    elif completion_mode == "complete":
        system_prompt = (
            f"You are an AI coding assistant specializing in {language}. "
            f"{tech_context}"
            f"Complete the current line or statement. "
            f"Return only the completion text, without explanations or markdown."
        )
        
        user_prompt = f"""File: {filename}

Complete this {language} code:
{before_cursor}"""
        
    else:  # continue mode
        system_prompt = (
            f"You are an AI coding assistant specializing in {language}. "
            f"{tech_context}"
            f"Continue writing the code logically from where it left off. "
            f"Return only the next few lines of code, without explanations or markdown."
        )
        
        user_prompt = f"""File: {filename}

Continue this {language} code:
{before_cursor}"""
    
    return f"System: {system_prompt}\n\nUser: {user_prompt}\n\nAssistant:"


def clean_completion(completion: str) -> str:
    """Clean up AI completion response"""
    
    # Remove markdown code blocks
    if completion.startswith("```"):
        lines = completion.split("\n")
        if len(lines) > 1:
            # Remove first line (```language) and last line (```)
            completion = "\n".join(lines[1:-1]) if lines[-1].strip() == "```" else "\n".join(lines[1:])
    
    # Remove common unwanted prefixes
    unwanted_prefixes = [
        "Here's the completion:",
        "The completed code is:",
        "Here's how to complete this:",
        "```",
    ]
    
    for prefix in unwanted_prefixes:
        if completion.lower().startswith(prefix.lower()):
            completion = completion[len(prefix):].strip()
    
    # Remove trailing explanations (lines that start with explanation markers)
    lines = completion.split("\n")
    cleaned_lines = []
    
    for line in lines:
        stripped = line.strip()
        # Stop at explanation markers
        if any(stripped.lower().startswith(marker) for marker in [
            "this code", "the above", "explanation:", "note:", "// this", "# this"
        ]):
            break
        cleaned_lines.append(line)
    
    return "\n".join(cleaned_lines).strip()


def get_file_extension(language: str) -> str:
    """Get file extension for language"""
    extensions = {
        "javascript": "js",
        "typescript": "ts",
        "python": "py",
        "java": "java",
        "csharp": "cs",
        "cpp": "cpp",
        "c": "c",
        "go": "go",
        "rust": "rs",
        "php": "php",
        "ruby": "rb",
        "html": "html",
        "css": "css",
        "scss": "scss",
        "json": "json",
        "yaml": "yml",
        "xml": "xml",
        "markdown": "md",
        "shell": "sh",
        "sql": "sql",
    }
    return extensions.get(language.lower(), "txt")