# Phase 5 Implementation Plan: Chat System with Code Intelligence

## Overview

Phase 5 implements the real-time chat system with code-aware AI assistance, building on the code parsing and embeddings infrastructure from Phase 4. This phase focuses on practical chat functionality for our small team without over-engineering.

**Duration**: 3 Weeks (15 Business Days)

**Prerequisites**:
- Phase 4 code parsing and embeddings complete
- OpenAI API key configured
- WebSocket infrastructure tested

## Objectives

1. Implement WebSocket-based real-time chat
2. Build code-aware context extraction
3. Create slash command system (/explain, /generate-tests, etc.)
4. Integrate LLM with streaming responses
5. Develop split-pane chat/code interface
6. Add secret redaction for security

---

## Week 1: Chat Infrastructure & WebSocket (Days 1-5)

### Day 1-2: WebSocket Infrastructure & Chat Models

**Tasks:**
1. Complete WebSocket connection management
2. Implement chat session lifecycle
3. Add message persistence with edit/delete
4. Create timeline integration for chat events

**Deliverables:**

`backend/app/models/chat.py` (≤300 lines) - ALREADY EXISTS, needs updates:
```python
from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey, Boolean, DateTime, Index
from sqlalchemy.orm import relationship, validates
from .base import Base, TimestampMixin
import json


class ChatSession(Base, TimestampMixin):
    """Chat session for a project with AI assistance."""

    __tablename__ = 'chat_sessions'
    __table_args__ = (
        Index("idx_chat_session_project", "project_id"),
        Index("idx_chat_session_updated", "updated_at"),
    )

    id = Column(Integer, primary_key=True)
    project_id = Column(Integer, ForeignKey('projects.id'), nullable=False)
    title = Column(String(200))
    is_active = Column(Boolean, default=True)

    # Summary for quick overview
    summary = Column(Text)
    summary_updated_at = Column(DateTime)

    # Relationships
    project = relationship("Project", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base, TimestampMixin):
    """Individual message in a chat session."""

    __tablename__ = 'chat_messages'
    __table_args__ = (
        Index("idx_chat_message_session", "session_id"),
        Index("idx_chat_message_created", "created_at"),
    )

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey('chat_sessions.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)

    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)

    # Code awareness
    code_snippets = Column(JSON)  # [{language, code, file_path, line_start, line_end}]
    referenced_files = Column(JSON)  # [file_paths]
    referenced_chunks = Column(JSON)  # [chunk_ids] from semantic search
    applied_commands = Column(JSON)  # {command: args}

    # Edit tracking
    is_edited = Column(Boolean, default=False)
    edited_at = Column(DateTime)
    original_content = Column(Text)  # Store original if edited

    # Soft delete
    is_deleted = Column(Boolean, default=False)

    # Relationships
    session = relationship("ChatSession", back_populates="messages")
    user = relationship("User")

    @validates("role")
    def validate_role(self, key, role):
        valid_roles = {'user', 'assistant', 'system'}
        if role not in valid_roles:
            raise ValueError(f"Invalid role: {role}")
        return role
```

`backend/app/websocket/manager.py` (≤250 lines) - ENHANCE EXISTING:
```python
from typing import Dict, List, Set
from fastapi import WebSocket
import json
import asyncio
import logging

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manage WebSocket connections for chat sessions."""

    def __init__(self):
        # session_id -> list of websockets
        self.active_connections: Dict[int, List[WebSocket]] = {}
        # user_id -> set of session_ids
        self.user_sessions: Dict[int, Set[int]] = {}
        # Lock for thread safety
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, session_id: int, user_id: int):
        """Accept new connection."""
        await websocket.accept()

        async with self._lock:
            if session_id not in self.active_connections:
                self.active_connections[session_id] = []
            self.active_connections[session_id].append(websocket)

            if user_id not in self.user_sessions:
                self.user_sessions[user_id] = set()
            self.user_sessions[user_id].add(session_id)

        logger.info(f"User {user_id} connected to session {session_id}")

    async def disconnect(self, websocket: WebSocket, session_id: int, user_id: int):
        """Remove connection."""
        async with self._lock:
            if session_id in self.active_connections:
                self.active_connections[session_id].remove(websocket)
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]

            if user_id in self.user_sessions:
                self.user_sessions[user_id].discard(session_id)
                if not self.user_sessions[user_id]:
                    del self.user_sessions[user_id]

    async def send_message(self, message: dict, session_id: int):
        """Send message to all connections in a session."""
        if session_id in self.active_connections:
            disconnected = []

            for websocket in self.active_connections[session_id]:
                try:
                    await websocket.send_json(message)
                except Exception as e:
                    logger.error(f"Failed to send message: {e}")
                    disconnected.append(websocket)

            # Clean up disconnected sockets
            for ws in disconnected:
                self.active_connections[session_id].remove(ws)

    async def broadcast_to_user(self, message: dict, user_id: int):
        """Send message to all sessions for a user."""
        if user_id in self.user_sessions:
            for session_id in self.user_sessions[user_id]:
                await self.send_message(message, session_id)

    def get_session_users(self, session_id: int) -> int:
        """Get count of users in session."""
        return len(self.active_connections.get(session_id, []))


# Global instance
connection_manager = ConnectionManager()
```

### Day 3: Message Handling & Persistence

**Tasks:**
1. Implement message CRUD operations
2. Add edit/delete functionality
3. Create message validation
4. Build chat timeline integration

**Deliverables:**

`backend/app/services/chat_service.py` (≤400 lines):
```python
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import List, Optional, Dict
import json
from datetime import datetime

from app.models.chat import ChatSession, ChatMessage
from app.models.timeline import TimelineEvent
from app.schemas.chat import MessageCreate, MessageUpdate
from app.websocket.manager import connection_manager


class ChatService:
    """Business logic for chat operations."""

    def __init__(self, db: Session):
        self.db = db

    async def create_session(self, project_id: int, title: Optional[str] = None) -> ChatSession:
        """Create new chat session."""
        session = ChatSession(
            project_id=project_id,
            title=title or f"Chat {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        )
        self.db.add(session)
        self.db.commit()

        # Add timeline event
        event = TimelineEvent(
            project_id=project_id,
            event_type="chat_created",
            title=f"Started chat: {session.title}",
            event_metadata={"session_id": session.id}
        )
        self.db.add(event)
        self.db.commit()

        return session

    async def create_message(
        self,
        session_id: int,
        content: str,
        role: str,
        user_id: Optional[int] = None,
        metadata: Optional[Dict] = None
    ) -> ChatMessage:
        """Create and broadcast new message."""
        message = ChatMessage(
            session_id=session_id,
            content=content,
            role=role,
            user_id=user_id,
            code_snippets=metadata.get('code_snippets', []) if metadata else [],
            referenced_files=metadata.get('referenced_files', []) if metadata else [],
            applied_commands=metadata.get('commands', {}) if metadata else {}
        )
        self.db.add(message)
        self.db.commit()

        # Update session timestamp
        session = self.db.query(ChatSession).filter_by(id=session_id).first()
        session.updated_at = datetime.utcnow()
        self.db.commit()

        # Broadcast to connected clients
        await self._broadcast_message(message)

        return message

    async def update_message(
        self,
        message_id: int,
        content: str,
        user_id: int
    ) -> Optional[ChatMessage]:
        """Edit existing message."""
        message = self.db.query(ChatMessage).filter_by(
            id=message_id,
            user_id=user_id,
            is_deleted=False
        ).first()

        if not message:
            return None

        # Store original content
        if not message.is_edited:
            message.original_content = message.content

        message.content = content
        message.is_edited = True
        message.edited_at = datetime.utcnow()

        self.db.commit()

        # Broadcast update
        await self._broadcast_message_update(message)

        return message

    async def delete_message(self, message_id: int, user_id: int) -> bool:
        """Soft delete message."""
        message = self.db.query(ChatMessage).filter_by(
            id=message_id,
            user_id=user_id
        ).first()

        if not message:
            return False

        message.is_deleted = True
        self.db.commit()

        # Broadcast deletion
        await connection_manager.send_message({
            'type': 'message_deleted',
            'message_id': message_id
        }, message.session_id)

        return True

    def get_session_messages(
        self,
        session_id: int,
        limit: int = 50,
        before_id: Optional[int] = None
    ) -> List[ChatMessage]:
        """Get messages with pagination."""
        query = self.db.query(ChatMessage).filter_by(
            session_id=session_id,
            is_deleted=False
        )

        if before_id:
            query = query.filter(ChatMessage.id < before_id)

        return query.order_by(ChatMessage.id.desc()).limit(limit).all()

    async def _broadcast_message(self, message: ChatMessage):
        """Broadcast new message to session."""
        await connection_manager.send_message({
            'type': 'new_message',
            'message': {
                'id': message.id,
                'content': message.content,
                'role': message.role,
                'user_id': message.user_id,
                'created_at': message.created_at.isoformat(),
                'code_snippets': message.code_snippets,
                'referenced_files': message.referenced_files
            }
        }, message.session_id)

    async def _broadcast_message_update(self, message: ChatMessage):
        """Broadcast message edit."""
        await connection_manager.send_message({
            'type': 'message_updated',
            'message': {
                'id': message.id,
                'content': message.content,
                'edited_at': message.edited_at.isoformat()
            }
        }, message.session_id)
```

### Day 4-5: WebSocket Endpoints & Frontend Integration

**Tasks:**
1. Create WebSocket message handlers
2. Implement connection authentication
3. Build frontend WebSocket hook
4. Add connection state management

**Deliverables:**

`backend/app/websocket/handlers.py` (≤300 lines):
```python
from fastapi import WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
import json
import logging
from typing import Optional

from app.database import get_db
from app.models.user import User
from app.auth.utils import get_current_user_ws
from app.services.chat_service import ChatService
from app.chat.processor import ChatProcessor
from .manager import connection_manager

logger = logging.getLogger(__name__)


async def handle_chat_connection(
    websocket: WebSocket,
    session_id: int,
    current_user: User,
    db: Session
):
    """Handle WebSocket connection for chat session."""
    await connection_manager.connect(websocket, session_id, current_user.id)
    chat_service = ChatService(db)
    chat_processor = ChatProcessor(db)

    try:
        # Send connection confirmation
        await websocket.send_json({
            'type': 'connected',
            'user_id': current_user.id,
            'session_id': session_id
        })

        # Send recent messages
        recent_messages = chat_service.get_session_messages(session_id, limit=20)
        await websocket.send_json({
            'type': 'message_history',
            'messages': [serialize_message(m) for m in reversed(recent_messages)]
        })

        # Message handling loop
        while True:
            data = await websocket.receive_json()

            if data['type'] == 'message':
                # Process user message
                user_message = await chat_service.create_message(
                    session_id=session_id,
                    content=data['content'],
                    role='user',
                    user_id=current_user.id,
                    metadata=data.get('metadata')
                )

                # Process with AI
                await chat_processor.process_message(
                    session_id=session_id,
                    message=user_message,
                    websocket=websocket
                )

            elif data['type'] == 'edit_message':
                await chat_service.update_message(
                    message_id=data['message_id'],
                    content=data['content'],
                    user_id=current_user.id
                )

            elif data['type'] == 'delete_message':
                await chat_service.delete_message(
                    message_id=data['message_id'],
                    user_id=current_user.id
                )

            elif data['type'] == 'typing':
                # Broadcast typing indicator
                await connection_manager.send_message({
                    'type': 'user_typing',
                    'user_id': current_user.id,
                    'is_typing': data['is_typing']
                }, session_id)

    except WebSocketDisconnect:
        logger.info(f"User {current_user.id} disconnected from session {session_id}")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        await websocket.send_json({
            'type': 'error',
            'message': 'Internal server error'
        })
    finally:
        await connection_manager.disconnect(websocket, session_id, current_user.id)


def serialize_message(message: ChatMessage) -> dict:
    """Convert message to JSON-serializable format."""
    return {
        'id': message.id,
        'content': message.content,
        'role': message.role,
        'user_id': message.user_id,
        'created_at': message.created_at.isoformat(),
        'is_edited': message.is_edited,
        'edited_at': message.edited_at.isoformat() if message.edited_at else None,
        'code_snippets': message.code_snippets,
        'referenced_files': message.referenced_files
    }
```

`frontend/src/hooks/useChat.js` (≤250 lines):
```jsx
import { useState, useEffect, useCallback, useRef } from 'react';
import { useAuth } from './useAuth';

export function useChat(sessionId) {
  const { user } = useAuth();
  const [messages, setMessages] = useState([]);
  const [connectionState, setConnectionState] = useState('disconnected');
  const [typingUsers, setTypingUsers] = useState(new Set());
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  const connect = useCallback(() => {
    if (!sessionId || !user) return;

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsUrl = `${protocol}//${window.location.host}/ws/sessions/${sessionId}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnectionState('connected');
      console.log('WebSocket connected');
    };

    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      handleMessage(data);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      setConnectionState('error');
    };

    ws.onclose = () => {
      setConnectionState('disconnected');
      wsRef.current = null;

      // Attempt reconnection
      reconnectTimeoutRef.current = setTimeout(() => {
        connect();
      }, 3000);
    };
  }, [sessionId, user]);

  const handleMessage = useCallback((data) => {
    switch (data.type) {
      case 'connected':
        console.log('Connected to session:', data.session_id);
        break;

      case 'message_history':
        setMessages(data.messages);
        break;

      case 'new_message':
        setMessages(prev => [...prev, data.message]);
        break;

      case 'message_updated':
        setMessages(prev => prev.map(msg =>
          msg.id === data.message.id
            ? { ...msg, ...data.message }
            : msg
        ));
        break;

      case 'message_deleted':
        setMessages(prev => prev.filter(msg => msg.id !== data.message_id));
        break;

      case 'user_typing':
        setTypingUsers(prev => {
          const next = new Set(prev);
          if (data.is_typing) {
            next.add(data.user_id);
          } else {
            next.delete(data.user_id);
          }
          return next;
        });
        break;

      case 'ai_stream':
        handleAIStream(data);
        break;
    }
  }, []);

  const handleAIStream = useCallback((data) => {
    if (data.done) {
      // Final message
      setMessages(prev => [...prev, data.message]);
    } else {
      // Streaming update
      setMessages(prev => {
        const last = prev[prev.length - 1];
        if (last && last.id === data.message_id && last.role === 'assistant') {
          return [
            ...prev.slice(0, -1),
            { ...last, content: last.content + data.content }
          ];
        } else {
          // First chunk
          return [...prev, {
            id: data.message_id,
            content: data.content,
            role: 'assistant',
            created_at: new Date().toISOString()
          }];
        }
      });
    }
  }, []);

  const sendMessage = useCallback((content, metadata = {}) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('WebSocket not connected');
      return;
    }

    wsRef.current.send(JSON.stringify({
      type: 'message',
      content,
      metadata
    }));
  }, []);

  const editMessage = useCallback((messageId, content) => {
    if (!wsRef.current) return;

    wsRef.current.send(JSON.stringify({
      type: 'edit_message',
      message_id: messageId,
      content
    }));
  }, []);

  const deleteMessage = useCallback((messageId) => {
    if (!wsRef.current) return;

    wsRef.current.send(JSON.stringify({
      type: 'delete_message',
      message_id: messageId
    }));
  }, []);

  const sendTypingIndicator = useCallback((isTyping) => {
    if (!wsRef.current) return;

    // Clear previous timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    wsRef.current.send(JSON.stringify({
      type: 'typing',
      is_typing: isTyping
    }));

    // Auto-stop typing after 5 seconds
    if (isTyping) {
      typingTimeoutRef.current = setTimeout(() => {
        sendTypingIndicator(false);
      }, 5000);
    }
  }, []);

  useEffect(() => {
    connect();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
      }
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (typingTimeoutRef.current) {
        clearTimeout(typingTimeoutRef.current);
      }
    };
  }, [connect]);

  return {
    messages,
    connectionState,
    typingUsers,
    sendMessage,
    editMessage,
    deleteMessage,
    sendTypingIndicator
  };
}
```

---

## Week 2: Context Building & Slash Commands (Days 6-10)

### Day 6-7: Context Extraction & File References

**Tasks:**
1. Build context extraction from messages
2. Implement file reference detection
3. Create code snippet extraction
4. Add context windowing logic

**Deliverables:**

`backend/app/chat/context_builder.py` (≤400 lines):
```python
import re
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
import logging

from app.models.code import CodeDocument, CodeEmbedding
from app.models.chat import ChatMessage

logger = logging.getLogger(__name__)


class ContextBuilder:
    """Extract and build context from chat messages."""

    # Patterns for detecting code references
    FILE_PATTERN = re.compile(r'(?:^|[\s`"])([a-zA-Z0-9_\-./]+\.[a-zA-Z]+)(?:[:,]?\s*(?:line\s*)?(\d+))?')
    CODE_BLOCK_PATTERN = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)
    SYMBOL_PATTERN = re.compile(r'(?:function|class|def|interface|type)\s+([a-zA-Z_]\w*)')

    def __init__(self, db: Session):
        self.db = db
        self.context_window = 50  # Lines around reference

    def extract_context(self, message: str, project_id: int) -> Dict:
        """Extract all context from a message."""
        context = {
            'file_references': self.extract_file_references(message),
            'code_blocks': self.extract_code_blocks(message),
            'symbols': self.extract_symbols(message),
            'chunks': []
        }

        # Get file chunks for references
        for file_ref in context['file_references']:
            chunks = self.get_file_context(
                project_id,
                file_ref['path'],
                file_ref.get('line')
            )
            context['chunks'].extend(chunks)

        # Search for symbol references
        for symbol in context['symbols']:
            chunks = self.search_symbol(project_id, symbol)
            context['chunks'].extend(chunks[:3])  # Top 3 matches

        # Deduplicate chunks
        seen = set()
        unique_chunks = []
        for chunk in context['chunks']:
            key = (chunk['document_id'], chunk['start_line'])
            if key not in seen:
                seen.add(key)
                unique_chunks.append(chunk)

        context['chunks'] = unique_chunks
        return context

    def extract_file_references(self, text: str) -> List[Dict]:
        """Extract file paths and line numbers from text."""
        references = []

        for match in self.FILE_PATTERN.finditer(text):
            file_path = match.group(1)
            line_num = match.group(2)

            # Skip common false positives
            if file_path.count('.') > 3 or file_path.startswith('http'):
                continue

            references.append({
                'path': file_path,
                'line': int(line_num) if line_num else None,
                'match': match.group(0)
            })

        return references

    def extract_code_blocks(self, text: str) -> List[Dict]:
        """Extract code blocks from markdown."""
        blocks = []

        for match in self.CODE_BLOCK_PATTERN.finditer(text):
            language = match.group(1) or 'text'
            code = match.group(2).strip()

            blocks.append({
                'language': language,
                'code': code,
                'length': len(code.split('\n'))
            })

        return blocks

    def extract_symbols(self, text: str) -> List[str]:
        """Extract mentioned function/class names."""
        symbols = []

        # Direct symbol mentions
        for match in self.SYMBOL_PATTERN.finditer(text):
            symbols.append(match.group(1))

        # Backtick mentions
        backtick_pattern = re.compile(r'`([a-zA-Z_]\w*)`')
        for match in backtick_pattern.finditer(text):
            name = match.group(1)
            # Heuristic: likely a symbol if mixed case or underscore
            if '_' in name or (name[0].isupper() and name[1:].islower()):
                symbols.append(name)

        return list(set(symbols))

    def get_file_context(
        self,
        project_id: int,
        file_path: str,
        line_number: Optional[int] = None
    ) -> List[Dict]:
        """Get context chunks for a file reference."""
        # Find document
        doc = self.db.query(CodeDocument).filter_by(
            project_id=project_id,
            file_path=file_path
        ).first()

        if not doc:
            # Try partial match
            doc = self.db.query(CodeDocument).filter(
                CodeDocument.project_id == project_id,
                CodeDocument.file_path.like(f'%{file_path}')
            ).first()

        if not doc:
            return []

        # Get relevant chunks
        if line_number:
            # Get chunk containing line
            chunks = self.db.query(CodeEmbedding).filter(
                CodeEmbedding.document_id == doc.id,
                CodeEmbedding.start_line <= line_number,
                CodeEmbedding.end_line >= line_number
            ).all()
        else:
            # Get first few chunks
            chunks = self.db.query(CodeEmbedding).filter_by(
                document_id=doc.id
            ).order_by(CodeEmbedding.start_line).limit(3).all()

        return [self._format_chunk(chunk) for chunk in chunks]

    def search_symbol(self, project_id: int, symbol: str) -> List[Dict]:
        """Search for symbol in project."""
        chunks = self.db.query(CodeEmbedding).join(CodeDocument).filter(
            CodeDocument.project_id == project_id,
            CodeEmbedding.symbol_name == symbol
        ).all()

        if not chunks:
            # Try partial match
            chunks = self.db.query(CodeEmbedding).join(CodeDocument).filter(
                CodeDocument.project_id == project_id,
                CodeEmbedding.symbol_name.like(f'%{symbol}%')
            ).limit(5).all()

        return [self._format_chunk(chunk) for chunk in chunks]

    def build_conversation_context(
        self,
        session_id: int,
        max_messages: int = 10
    ) -> List[Dict]:
        """Build context from recent conversation."""
        messages = self.db.query(ChatMessage).filter_by(
            session_id=session_id,
            is_deleted=False
        ).order_by(ChatMessage.id.desc()).limit(max_messages).all()

        return [
            {
                'role': msg.role,
                'content': msg.content,
                'code_snippets': msg.code_snippets
            }
            for msg in reversed(messages)
        ]

    def _format_chunk(self, chunk: CodeEmbedding) -> Dict:
        """Format chunk for context."""
        return {
            'document_id': chunk.document_id,
            'file_path': chunk.document.file_path,
            'language': chunk.document.language,
            'symbol_name': chunk.symbol_name,
            'symbol_type': chunk.symbol_type,
            'start_line': chunk.start_line,
            'end_line': chunk.end_line,
            'content': chunk.chunk_content
        }
```

### Day 8-9: Slash Command Implementation

**Tasks:**
1. Create command parser
2. Implement /explain, /generate-tests, /summarize-pr, /grep
3. Build command execution framework
4. Add command suggestions

**Deliverables:**

`backend/app/chat/commands.py` (≤500 lines):
```python
import re
import asyncio
from typing import Dict, List, Optional, Callable, Any
from sqlalchemy.orm import Session
import logging

from app.models.code import CodeDocument, CodeEmbedding
from app.models.project import Project
from app.search.hybrid import HybridSearch
from app.llm.client import LLMClient

logger = logging.getLogger(__name__)


class SlashCommand:
    """Base class for slash commands."""

    def __init__(self, name: str, description: str, usage: str):
        self.name = name
        self.description = description
        self.usage = usage

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        """Execute command and return result."""
        raise NotImplementedError


class ExplainCommand(SlashCommand):
    """Explain code with context."""

    def __init__(self):
        super().__init__(
            name="explain",
            description="Explain code functionality",
            usage="/explain [file:line] or /explain [symbol]"
        )

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        # Parse arguments
        file_match = re.match(r'(\S+):(\d+)', args)

        if file_match:
            file_path = file_match.group(1)
            line_num = int(file_match.group(2))

            # Get code context
            chunks = context.get('chunks', [])
            relevant_chunk = None

            for chunk in chunks:
                if (chunk['file_path'].endswith(file_path) and
                    chunk['start_line'] <= line_num <= chunk['end_line']):
                    relevant_chunk = chunk
                    break

            if not relevant_chunk:
                return {
                    'success': False,
                    'message': f"Could not find {file_path}:{line_num}"
                }

            prompt = f"""Explain the following {relevant_chunk['language']} code:

File: {relevant_chunk['file_path']}
Lines {relevant_chunk['start_line']}-{relevant_chunk['end_line']}

{relevant_chunk['content']}

Provide a clear explanation of what this code does, including:
1. Purpose and functionality
2. Input/output behavior
3. Key implementation details
4. Any notable patterns or techniques used"""

        else:
            # Symbol-based explanation
            symbol = args.strip()
            chunks = context.get('chunks', [])

            relevant_chunks = [
                c for c in chunks
                if c.get('symbol_name') == symbol
            ]

            if not relevant_chunks:
                return {
                    'success': False,
                    'message': f"Could not find symbol: {symbol}"
                }

            chunk = relevant_chunks[0]
            prompt = f"""Explain the {chunk['symbol_type']} '{chunk['symbol_name']}':

{chunk['content']}

Provide a comprehensive explanation."""

        return {
            'success': True,
            'prompt': prompt,
            'requires_llm': True
        }


class GenerateTestsCommand(SlashCommand):
    """Generate unit tests for code."""

    def __init__(self):
        super().__init__(
            name="generate-tests",
            description="Generate unit tests for functions/classes",
            usage="/generate-tests [function_name]"
        )

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        symbol = args.strip()
        chunks = context.get('chunks', [])

        # Find function/class
        relevant_chunks = [
            c for c in chunks
            if c.get('symbol_name') == symbol and
            c.get('symbol_type') in ['function', 'class', 'method']
        ]

        if not relevant_chunks:
            return {
                'success': False,
                'message': f"Could not find function/class: {symbol}"
            }

        chunk = relevant_chunks[0]
        language = chunk['language']

        # Language-specific test framework
        framework_map = {
            'python': 'pytest',
            'javascript': 'Jest',
            'typescript': 'Jest with TypeScript'
        }
        framework = framework_map.get(language, 'appropriate test framework')

        prompt = f"""Generate comprehensive unit tests for the following {chunk['symbol_type']}:

Language: {language}
File: {chunk['file_path']}

{chunk['content']}

Generate tests using {framework} that cover:
1. Normal operation cases
2. Edge cases
3. Error conditions
4. Any boundary conditions

Include setup/teardown if needed."""

        return {
            'success': True,
            'prompt': prompt,
            'requires_llm': True
        }


class SummarizePRCommand(SlashCommand):
    """Summarize changes in PR style."""

    def __init__(self):
        super().__init__(
            name="summarize-pr",
            description="Summarize recent changes in PR format",
            usage="/summarize-pr [#commits]"
        )

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        # This would integrate with git in full implementation
        # For now, summarize recent file changes

        project_id = context.get('project_id')

        # Get recent documents
        recent_docs = db.query(CodeDocument).filter_by(
            project_id=project_id
        ).order_by(CodeDocument.updated_at.desc()).limit(10).all()

        if not recent_docs:
            return {
                'success': False,
                'message': "No recent changes found"
            }

        files_summary = []
        for doc in recent_docs:
            files_summary.append(f"- {doc.file_path} ({doc.language})")

        prompt = f"""Create a pull request summary for the following changed files:

{chr(10).join(files_summary)}

Generate a PR description that includes:
1. Summary of changes (bullet points)
2. Type of change (feature/bugfix/refactor)
3. Testing notes
4. Any breaking changes

Format it as a proper GitHub PR description."""

        return {
            'success': True,
            'prompt': prompt,
            'requires_llm': True
        }


class GrepCommand(SlashCommand):
    """Search codebase for pattern."""

    def __init__(self):
        super().__init__(
            name="grep",
            description="Search code for pattern",
            usage="/grep [pattern] [--type=python]"
        )

    async def execute(self, args: str, context: Dict, db: Session) -> Dict:
        # Parse arguments
        parts = args.split()
        if not parts:
            return {
                'success': False,
                'message': "Usage: /grep pattern [--type=language]"
            }

        pattern = parts[0]
        language = None

        # Check for type flag
        for part in parts[1:]:
            if part.startswith('--type='):
                language = part.split('=')[1]

        project_id = context.get('project_id')

        # Search in chunks
        query = db.query(CodeEmbedding).join(CodeDocument).filter(
            CodeDocument.project_id == project_id,
            CodeEmbedding.chunk_content.like(f'%{pattern}%')
        )

        if language:
            query = query.filter(CodeDocument.language == language)

        results = query.limit(10).all()

        if not results:
            return {
                'success': True,
                'message': f"No matches found for '{pattern}'"
            }

        # Format results
        output = [f"Found {len(results)} matches for '{pattern}':\n"]

        for chunk in results:
            # Find matching lines
            lines = chunk.chunk_content.split('\n')
            matches = []

            for i, line in enumerate(lines):
                if pattern.lower() in line.lower():
                    line_num = chunk.start_line + i
                    matches.append(f"{line_num}: {line.strip()}")

            if matches:
                output.append(f"\n{chunk.document.file_path}:")
                output.extend(matches[:3])  # First 3 matches
                if len(matches) > 3:
                    output.append(f"  ... and {len(matches) - 3} more matches")

        return {
            'success': True,
            'message': '\n'.join(output),
            'requires_llm': False
        }


class CommandRegistry:
    """Registry and parser for slash commands."""

    def __init__(self):
        self.commands: Dict[str, SlashCommand] = {}
        self._register_default_commands()

    def _register_default_commands(self):
        """Register built-in commands."""
        self.register(ExplainCommand())
        self.register(GenerateTestsCommand())
        self.register(SummarizePRCommand())
        self.register(GrepCommand())

    def register(self, command: SlashCommand):
        """Register a command."""
        self.commands[command.name] = command

    def parse_message(self, message: str) -> List[Tuple[str, str]]:
        """Extract commands from message."""
        commands = []

        # Match /command args format
        pattern = re.compile(r'/(\w+)\s*([^/]*?)(?=/\w+|$)')

        for match in pattern.finditer(message):
            cmd_name = match.group(1)
            args = match.group(2).strip()

            if cmd_name in self.commands:
                commands.append((cmd_name, args))

        return commands

    async def execute_commands(
        self,
        message: str,
        context: Dict,
        db: Session
    ) -> List[Dict]:
        """Execute all commands in message."""
        commands = self.parse_message(message)
        results = []

        for cmd_name, args in commands:
            command = self.commands.get(cmd_name)
            if command:
                try:
                    result = await command.execute(args, context, db)
                    result['command'] = cmd_name
                    results.append(result)
                except Exception as e:
                    logger.error(f"Command execution failed: {e}")
                    results.append({
                        'command': cmd_name,
                        'success': False,
                        'message': f"Command failed: {str(e)}"
                    })

        return results

    def get_suggestions(self, partial: str) -> List[Dict]:
        """Get command suggestions."""
        if not partial.startswith('/'):
            return []

        partial_cmd = partial[1:].lower()
        suggestions = []

        for name, command in self.commands.items():
            if name.startswith(partial_cmd):
