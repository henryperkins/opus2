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
```

```python
                suggestions.append({
                    'command': f'/{name}',
                    'description': command.description,
                    'usage': command.usage
                })

        return suggestions[:5]  # Top 5 suggestions


# Global registry
command_registry = CommandRegistry()
```

### Day 10: Secret Scanning & Redaction

**Tasks:**
1. Implement secret pattern detection
2. Build redaction system
3. Add pre-send validation
4. Create secret type identification

**Deliverables:**

`backend/app/chat/secret_scanner.py` (≤300 lines):
```python
import re
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)


class SecretScanner:
    """Detect and redact secrets from messages."""

    # Common secret patterns
    PATTERNS = {
        'api_key': [
            (r'[aA][pP][iI][-_]?[kK][eE][yY]\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', 'API Key'),
            (r'[aA][pP][iI][-_]?[sS][eE][cC][rR][eE][tT]\s*[:=]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', 'API Secret'),
        ],
        'aws': [
            (r'AKIA[0-9A-Z]{16}', 'AWS Access Key'),
            (r'aws_secret_access_key\s*=\s*["\']?([a-zA-Z0-9/+=]{40})["\']?', 'AWS Secret Key'),
        ],
        'github': [
            (r'ghp_[a-zA-Z0-9]{36}', 'GitHub Personal Token'),
            (r'gho_[a-zA-Z0-9]{36}', 'GitHub OAuth Token'),
            (r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}', 'GitHub Fine-grained Token'),
        ],
        'database': [
            (r'(?:postgres|mysql|mongodb)://[^:]+:([^@]+)@', 'Database Password'),
            (r'[pP][aA][sS][sS][wW][oO][rR][dD]\s*[:=]\s*["\']?([^"\'\s]{8,})["\']?', 'Password'),
        ],
        'jwt': [
            (r'eyJ[a-zA-Z0-9_\-]+\.eyJ[a-zA-Z0-9_\-]+\.[a-zA-Z0-9_\-]+', 'JWT Token'),
        ],
        'private_key': [
            (r'-----BEGIN\s+(?:RSA\s+)?PRIVATE\s+KEY-----', 'Private Key'),
            (r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----', 'SSH Private Key'),
        ],
    }

    def __init__(self):
        self.compiled_patterns = self._compile_patterns()

    def _compile_patterns(self) -> Dict[str, List[Tuple[re.Pattern, str]]]:
        """Compile regex patterns for performance."""
        compiled = {}

        for category, patterns in self.PATTERNS.items():
            compiled[category] = [
                (re.compile(pattern, re.IGNORECASE), name)
                for pattern, name in patterns
            ]

        return compiled

    def scan(self, text: str) -> List[Dict]:
        """Scan text for secrets."""
        findings = []

        for category, patterns in self.compiled_patterns.items():
            for pattern, secret_type in patterns:
                for match in pattern.finditer(text):
                    findings.append({
                        'type': secret_type,
                        'category': category,
                        'match': match.group(0),
                        'start': match.start(),
                        'end': match.end(),
                        'severity': self._get_severity(category)
                    })

        # Check for high entropy strings
        entropy_findings = self._check_entropy(text)
        findings.extend(entropy_findings)

        return findings

    def redact(self, text: str, findings: List[Dict]) -> str:
        """Redact secrets from text."""
        if not findings:
            return text

        # Sort findings by position (reverse to maintain positions)
        sorted_findings = sorted(findings, key=lambda x: x['start'], reverse=True)

        redacted = text
        for finding in sorted_findings:
            start = finding['start']
            end = finding['end']
            secret_type = finding['type']

            # Create redaction placeholder
            redaction = f"[REDACTED {secret_type}]"

            # Replace secret with redaction
            redacted = redacted[:start] + redaction + redacted[end:]

        return redacted

    def validate_message(self, text: str) -> Dict:
        """Validate message for secrets before sending."""
        findings = self.scan(text)

        if not findings:
            return {
                'valid': True,
                'findings': []
            }

        # Check severity
        high_severity = [f for f in findings if f['severity'] == 'high']

        return {
            'valid': len(high_severity) == 0,
            'findings': findings,
            'message': f"Found {len(findings)} potential secrets ({len(high_severity)} high severity)"
        }

    def _check_entropy(self, text: str) -> List[Dict]:
        """Check for high entropy strings that might be secrets."""
        findings = []

        # Look for base64-like strings
        base64_pattern = re.compile(r'[a-zA-Z0-9+/]{40,}={0,2}')

        for match in base64_pattern.finditer(text):
            string = match.group(0)
            entropy = self._calculate_entropy(string)

            if entropy > 4.5:  # High entropy threshold
                findings.append({
                    'type': 'High Entropy String',
                    'category': 'entropy',
                    'match': string[:20] + '...' if len(string) > 20 else string,
                    'start': match.start(),
                    'end': match.end(),
                    'severity': 'medium',
                    'entropy': entropy
                })

        return findings

    def _calculate_entropy(self, string: str) -> float:
        """Calculate Shannon entropy of a string."""
        if not string:
            return 0

        # Count character frequencies
        freq = {}
        for char in string:
            freq[char] = freq.get(char, 0) + 1

        # Calculate entropy
        entropy = 0
        length = len(string)

        for count in freq.values():
            probability = count / length
            if probability > 0:
                entropy -= probability * (probability and probability.bit_length())

        return entropy

    def _get_severity(self, category: str) -> str:
        """Get severity level for secret category."""
        high_severity = {'private_key', 'aws', 'database'}
        medium_severity = {'api_key', 'github', 'jwt'}

        if category in high_severity:
            return 'high'
        elif category in medium_severity:
            return 'medium'
        else:
            return 'low'

    def get_redaction_summary(self, findings: List[Dict]) -> str:
        """Generate summary of redacted content."""
        if not findings:
            return ""

        by_type = {}
        for finding in findings:
            secret_type = finding['type']
            by_type[secret_type] = by_type.get(secret_type, 0) + 1

        summary_parts = []
        for secret_type, count in by_type.items():
            summary_parts.append(f"{count} {secret_type}")

        return f"Redacted: {', '.join(summary_parts)}"


# Global scanner instance
secret_scanner = SecretScanner()
```

---

## Week 3: LLM Integration & UI (Days 11-15)

### Day 11-12: LLM Client & Streaming

**Tasks:**
1. Create LLM client abstraction
2. Implement streaming responses
3. Add provider switching (OpenAI/Azure)
4. Build retry logic

**Deliverables:**

`backend/app/llm/client.py` (≤350 lines):
```python
from typing import Optional, AsyncIterator, Dict, List
import openai
from openai import AsyncOpenAI, AsyncAzureOpenAI
import logging
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings

logger = logging.getLogger(__name__)


class LLMClient:
    """Unified client for LLM providers."""

    def __init__(self):
        self.provider = settings.llm_provider  # 'openai' or 'azure'
        self.model = settings.llm_model or 'gpt-4'
        self.client = self._create_client()

    def _create_client(self):
        """Create provider-specific client."""
        if self.provider == 'azure':
            return AsyncAzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version="2024-02-01",
                azure_endpoint=settings.azure_openai_endpoint
            )
        else:
            return AsyncOpenAI(api_key=settings.openai_api_key)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10)
    )
    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False
    ):
        """Get completion from LLM."""
        try:
            params = {
                'model': self.model,
                'messages': messages,
                'temperature': temperature,
                'stream': stream
            }

            if max_tokens:
                params['max_tokens'] = max_tokens

            if stream:
                return self._stream_response(
                    await self.client.chat.completions.create(**params)
                )
            else:
                response = await self.client.chat.completions.create(**params)
                return response.choices[0].message.content

        except openai.APIError as e:
            logger.error(f"LLM API error: {e}")
            raise
        except Exception as e:
            logger.error(f"LLM client error: {e}")
            raise

    async def _stream_response(self, stream) -> AsyncIterator[str]:
        """Handle streaming response."""
        try:
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Streaming error: {e}")
            yield f"\n\n[Error: {str(e)}]"

    def estimate_tokens(self, text: str) -> int:
        """Estimate token count."""
        # Rough estimate: 4 chars per token
        return len(text) // 4

    def prepare_code_context(self, chunks: List[Dict]) -> str:
        """Format code chunks for context."""
        if not chunks:
            return ""

        context_parts = ["Relevant code from the project:\n"]

        for chunk in chunks[:5]:  # Limit to 5 chunks
            context_parts.append(f"""
File: {chunk['file_path']} (lines {chunk['start_line']}-{chunk['end_line']})
Language: {chunk['language']}
{chunk.get('symbol_type', '')} {chunk.get('symbol_name', '')}

```{chunk['language']}
{chunk['content']}
/*
""")

        return '\n'.join(context_parts)


# Global client instance
llm_client = LLMClient()
```

`backend/app/llm/streaming.py` (≤250 lines):

```python
import asyncio
import json
from typing import AsyncIterator, Optional
from fastapi import WebSocket
import logging

logger = logging.getLogger(__name__)


class StreamingHandler:
    """Handle streaming LLM responses over WebSocket."""

    def __init__(self, websocket: WebSocket):
        self.websocket = websocket
        self.message_id = None
        self.buffer = []
        self.total_tokens = 0

    async def stream_response(
        self,
        response_generator: AsyncIterator[str],
        message_id: int
    ):
        """Stream LLM response chunks to WebSocket."""
        self.message_id = message_id

        try:
            async for chunk in response_generator:
                self.buffer.append(chunk)
                self.total_tokens += len(chunk) // 4  # Rough estimate

                # Send chunk
                await self.websocket.send_json({
                    'type': 'ai_stream',
                    'message_id': message_id,
                    'content': chunk,
                    'done': False
                })

                # Small delay to prevent overwhelming client
                await asyncio.sleep(0.01)

            # Send completion
            full_content = ''.join(self.buffer)
            await self.websocket.send_json({
                'type': 'ai_stream',
                'message_id': message_id,
                'content': '',
                'done': True,
                'message': {
                    'id': message_id,
                    'content': full_content,
                    'role': 'assistant',
                    'created_at': datetime.now().isoformat()
                }
            })

            return full_content

        except Exception as e:
            logger.error(f"Streaming error: {e}")

            # Send error message
            await self.websocket.send_json({
                'type': 'ai_stream',
                'message_id': message_id,
                'error': str(e),
                'done': True
            })

            raise

    async def handle_code_generation(
        self,
        content: str,
        language: str,
        websocket: WebSocket
    ):
        """Special handling for code generation responses."""
        # Track code blocks
        code_blocks = []
        current_block = []
        in_code_block = False
        current_language = None

        lines = content.split('\n')

        for line in lines:
            if line.startswith('```'):
                if in_code_block:
                    # End of code block
                    code_blocks.append({
                        'language': current_language or language,
                        'code': '\n'.join(current_block)
                    })
                    current_block = []
                    in_code_block = False
                else:
                    # Start of code block
                    in_code_block = True
                    current_language = line[3:].strip() or language
            elif in_code_block:
                current_block.append(line)

        # Send code blocks separately for highlighting
        for i, block in enumerate(code_blocks):
            await websocket.send_json({
                'type': 'code_block',
                'index': i,
                'language': block['language'],
                'code': block['code']
            })
```

### Day 13: Chat Message Processing

**Tasks:**
1. Integrate all components
2. Build message processing pipeline
3. Add context injection
4. Implement response generation

**Deliverables:**

`backend/app/chat/processor.py` (≤500 lines) - ENHANCE EXISTING:
```python
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import WebSocket
import logging
import asyncio

from app.models.chat import ChatSession, ChatMessage
from app.models.project import Project
from app.services.chat_service import ChatService
from app.llm.client import llm_client
from app.llm.streaming import StreamingHandler
from .context_builder import ContextBuilder
from .commands import command_registry
from .secret_scanner import secret_scanner

logger = logging.getLogger(__name__)


class ChatProcessor:
    """Process chat messages with AI assistance."""

    def __init__(self, db: Session):
        self.db = db
        self.chat_service = ChatService(db)
        self.context_builder = ContextBuilder(db)

    async def process_message(
        self,
        session_id: int,
        message: ChatMessage,
        websocket: WebSocket
    ):
        """Process user message and generate AI response."""
        try:
            # Get session and project
            session = self.db.query(ChatSession).filter_by(id=session_id).first()
            if not session:
                raise ValueError("Session not found")

            # Secret scanning
            validation = secret_scanner.validate_message(message.content)
            if not validation['valid']:
                # Redact and warn
                redacted = secret_scanner.redact(message.content, validation['findings'])

                # Update message with redacted content
                message.content = redacted
                self.db.commit()

                # Send warning
                await websocket.send_json({
                    'type': 'warning',
                    'message': f"Secrets detected and redacted: {validation['message']}"
                })

            # Extract context
            context = self.context_builder.extract_context(
                message.content,
                session.project_id
            )
            context['project_id'] = session.project_id

            # Store context references in message
            message.referenced_files = [ref['path'] for ref in context['file_references']]
            message.referenced_chunks = [c['document_id'] for c in context['chunks']]
            self.db.commit()

            # Execute slash commands
            commands = await command_registry.execute_commands(
                message.content,
                context,
                self.db
            )

            if commands:
                message.applied_commands = {
                    cmd['command']: cmd.get('prompt', cmd.get('message', ''))
                    for cmd in commands
                }
                self.db.commit()

                # Handle command results
                for cmd_result in commands:
                    if cmd_result.get('requires_llm'):
                        # Generate LLM response
                        await self._generate_ai_response(
                            session_id,
                            cmd_result['prompt'],
                            context,
                            websocket
                        )
                    else:
                        # Direct response
                        await self.chat_service.create_message(
                            session_id=session_id,
                            content=cmd_result['message'],
                            role='assistant'
                        )
            else:
                # Regular conversation
                await self._generate_ai_response(
                    session_id,
                    message.content,
                    context,
                    websocket
                )

        except Exception as e:
            logger.error(f"Message processing error: {e}")

            # Send error message
            await self.chat_service.create_message(
                session_id=session_id,
                content=f"I encountered an error processing your message: {str(e)}",
                role='assistant'
            )

    async def _generate_ai_response(
        self,
        session_id: int,
        prompt: str,
        context: Dict,
        websocket: WebSocket
    ):
        """Generate and stream AI response."""
        # Build conversation history
        conversation = self.context_builder.build_conversation_context(session_id)

        # Prepare messages for LLM
        messages = [
            {
                "role": "system",
                "content": """You are an AI coding assistant with access to the project codebase.
You can analyze code, explain functionality, generate tests, and help with development tasks.
Always provide clear, concise, and accurate responses.
When referencing code, mention the file path and line numbers."""
            }
        ]

        # Add code context if available
        if context['chunks']:
            code_context = llm_client.prepare_code_context(context['chunks'])
            messages.append({
                "role": "system",
                "content": code_context
            })

        # Add conversation history
        for msg in conversation[-5:]:  # Last 5 messages
            messages.append({
                "role": msg['role'],
                "content": msg['content']
            })

        # Add current prompt
        messages.append({
            "role": "user",
            "content": prompt
        })

        # Create placeholder message
        ai_message = await self.chat_service.create_message(
            session_id=session_id,
            content="",
            role='assistant'
        )

        # Stream response
        streaming_handler = StreamingHandler(websocket)

        try:
            response_stream = await llm_client.complete(
                messages=messages,
                stream=True,
                temperature=0.7
            )

            full_response = await streaming_handler.stream_response(
                response_stream,
                ai_message.id
            )

            # Update message with full response
            ai_message.content = full_response

            # Extract code snippets from response
            code_snippets = self._extract_code_snippets(full_response)
            if code_snippets:
                ai_message.code_snippets = code_snippets

            self.db.commit()

        except Exception as e:
            logger.error(f"AI generation error: {e}")
            ai_message.content = "I apologize, but I encountered an error generating a response."
            self.db.commit()

    def _extract_code_snippets(self, text: str) -> List[Dict]:
        """Extract code snippets from response."""
        import re

        snippets = []
        pattern = re.compile(r'```(\w+)?\n(.*?)```', re.DOTALL)

        for match in pattern.finditer(text):
            language = match.group(1) or 'text'
            code = match.group(2).strip()

            snippets.append({
                'language': language,
                'code': code
            })

        return snippets

    async def generate_summary(self, session_id: int) -> str:
        """Generate chat session summary."""
        messages = self.db.query(ChatMessage).filter_by(
            session_id=session_id,
            is_deleted=False
        ).order_by(ChatMessage.id).all()

        if len(messages) < 3:
            return "Chat session with minimal activity"

        # Build summary prompt
        conversation_text = []
        for msg in messages[:20]:  # First 20 messages
            role = "User" if msg.role == "user" else "AI"
            conversation_text.append(f"{role}: {msg.content[:200]}...")

        prompt = f"""Summarize this chat session in 2-3 sentences:

{chr(10).join(conversation_text)}

Focus on the main topics discussed and any key outcomes."""

        response = await llm_client.complete(
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=100
        )

        return response
```

### Day 14-15: Frontend Chat Interface

**Tasks:**
1. Build split-pane chat UI
2. Implement message components
3. Add code editor integration
4. Create command suggestions UI

**Deliverables:**

`frontend/src/components/chat/CodeChat.jsx` (≤400 lines) - ENHANCE EXISTING:
```jsx
import React, { useState, useEffect, useRef } from 'react';
import { useChat } from '../../hooks/useChat';
import { useCodeEditor } from '../../hooks/useCodeEditor';
import MessageList from './MessageList';
import CommandInput from './CommandInput';
import CodePreview from './CodePreview';
import MonacoEditor from '@monaco-editor/react';

export default function CodeChat({ sessionId, projectId }) {
  const {
    messages,
    connectionState,
    typingUsers,
    sendMessage,
    editMessage,
    deleteMessage,
    sendTypingIndicator
  } = useChat(sessionId);

  const [editorContent, setEditorContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('python');
  const [selectedMessage, setSelectedMessage] = useState(null);
  const [showDiff, setShowDiff] = useState(false);

  // Extract code from selected message
  useEffect(() => {
    if (selectedMessage?.code_snippets?.length > 0) {
      const snippet = selectedMessage.code_snippets[0];
      setEditorContent(snippet.code);
      setEditorLanguage(snippet.language);
    }
  }, [selectedMessage]);

  const handleSendMessage = (content, metadata) => {
    // Add current editor content if referenced
    if (content.includes('@editor')) {
      metadata.code_snippets = [{
        language: editorLanguage,
        code: editorContent
      }];
    }

    sendMessage(content, metadata);
  };

  const handleCodeSelect = (codeBlock) => {
    setEditorContent(codeBlock.code);
    setEditorLanguage(codeBlock.language);
  };

  const applyCodeSuggestion = (code) => {
    if (showDiff) {
      // Show diff view
      setShowDiff(true);
    } else {
      setEditorContent(code);
    }
  };

  return (
    <div className="flex h-full bg-gray-50">
      {/* Chat Panel */}
      <div className="w-1/2 flex flex-col bg-white border-r border-gray-200">
        <div className="flex-1 overflow-hidden">
          <MessageList
            messages={messages}
            onMessageSelect={setSelectedMessage}
            onCodeSelect={handleCodeSelect}
            onMessageEdit={editMessage}
            onMessageDelete={deleteMessage}
            currentUserId={user?.id}
          />
        </div>

        {/* Typing indicators */}
        {typingUsers.size > 0 && (
          <div className="px-4 py-2 text-sm text-gray-500">
            {typingUsers.size} user{typingUsers.size > 1 ? 's' : ''} typing...
          </div>
        )}

        {/* Connection status */}
        {connectionState !== 'connected' && (
          <div className="px-4 py-2 bg-yellow-50 text-yellow-800 text-sm">
            {connectionState === 'connecting' ? 'Connecting...' : 'Disconnected'}
          </div>
        )}

        <CommandInput
          onSend={handleSendMessage}
          onTyping={sendTypingIndicator}
          projectId={projectId}
        />
      </div>

      {/* Code Editor Panel */}
      <div className="w-1/2 flex flex-col">
        <div className="flex items-center justify-between px-4 py-2 bg-gray-100 border-b">
          <div className="flex items-center space-x-4">
            <select
              value={editorLanguage}
              onChange={(e) => setEditorLanguage(e.target.value)}
              className="text-sm border rounded px-2 py-1"
            >
              <option value="python">Python</option>
              <option value="javascript">JavaScript</option>
              <option value="typescript">TypeScript</option>
            </select>

            <button
              onClick={() => setShowDiff(!showDiff)}
              className={`text-sm px-3 py-1 rounded ${
                showDiff ? 'bg-blue-500 text-white' : 'bg-white border'
              }`}
            >
              Diff View
            </button>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => navigator.clipboard.writeText(editorContent)}
              className="text-sm text-gray-600 hover:text-gray-900"
              title="Copy code"
            >
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
            </button>
          </div>
        </div>

        <div className="flex-1">
          <MonacoEditor
            value={editorContent}
            language={editorLanguage}
            onChange={setEditorContent}
            theme="vs-dark"
            options={{
              minimap: { enabled: false },
              fontSize: 14,
              wordWrap: 'on',
              automaticLayout: true
            }}
          />
        </div>

        {/* Code preview for selected message */}
        {selectedMessage?.code_snippets && (
          <CodePreview
            snippets={selectedMessage.code_snippets}
            onApply={applyCodeSuggestion}
          />
        )}
      </div>
    </div>
  );
}
```

`frontend/src/components/chat/CommandInput.jsx` (≤300 lines):
```jsx
import React, { useState, useRef, useEffect } from 'react';
import { searchAPI } from '../../api/search';

export default function CommandInput({ onSend, onTyping, projectId }) {
  const [message, setMessage] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(-1);
  const inputRef = useRef(null);
  const [isTyping, setIsTyping] = useState(false);

  // Command suggestions
  const commands = [
    { name: '/explain', description: 'Explain code functionality' },
    { name: '/generate-tests', description: 'Generate unit tests' },
    { name: '/summarize-pr', description: 'Summarize changes' },
    { name: '/grep', description: 'Search codebase' }
  ];

  useEffect(() => {
    // Check for slash commands
    if (message.startsWith('/')) {
      const partial = message.split(' ')[0];
      const matches = commands.filter(cmd =>
        cmd.name.startsWith(partial)
      );
      setSuggestions(matches);
      setShowSuggestions(matches.length > 0);
    } else {
      setShowSuggestions(false);
    }
  }, [message]);

  // Handle typing indicator
  useEffect(() => {
    if (message && !isTyping) {
      setIsTyping(true);
      onTyping?.(true);
    } else if (!message && isTyping) {
      setIsTyping(false);
      onTyping?.(false);
    }
  }, [message, isTyping, onTyping]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!message.trim()) return;

    const metadata = {};

    // Check for file references
    const fileRefs = message.match(/[a-zA-Z0-9_\-./]+\.[a-zA-Z]+/g);
    if (fileRefs) {
      metadata.referenced_files = fileRefs;
    }

    onSend(message, metadata);
    setMessage('');
    setIsTyping(false);
    onTyping?.(false);
  };

  const handleKeyDown = (e) => {
    if (showSuggestions && suggestions.length > 0) {
      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex(prev =>
            prev < suggestions.length - 1 ? prev + 1 : prev
          );
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex(prev => prev > 0 ? prev - 1 : -1);
          break;
        case 'Tab':
        case 'Enter':
          if (selectedIndex >= 0) {
            e.preventDefault();
            const selected = suggestions[selectedIndex];
            setMessage(selected.name + ' ');
            setShowSuggestions(false);
            inputRef.current?.focus();
          }
          break;
        case 'Escape':
          setShowSuggestions(false);
          break;
      }
    }
  };

  return (
    <div className="relative border-t border-gray-200">
      {/* Command suggestions */}
      {showSuggestions && (
        <div className="absolute bottom-full left-0 right-0 bg-white border border-gray-200 shadow-lg rounded-t-lg">
          {suggestions.map((cmd, index) => (
            <div
              key={cmd.name}
              className={
```

Looking at the incomplete Phase 5 and your analysis, I'll complete the missing essential components while keeping modules under 900 lines. Here's the completion of Phase 5:

## Phase 5 Implementation (Continued): Missing Components

### Essential Backend Components

#### 1. Pydantic Schemas

`backend/app/schemas/chat.py` (≤150 lines):
```python
"""Chat-related Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class ChatSessionCreate(BaseModel):
    """Create a new chat session."""
    project_id: int
    title: Optional[str] = Field(None, max_length=200)


class ChatSessionUpdate(BaseModel):
    """Update chat session."""
    title: Optional[str] = Field(None, max_length=200)
    is_active: Optional[bool] = None


class MessageCreate(BaseModel):
    """Create a new message."""
    content: str = Field(..., min_length=1, max_length=10000)
    metadata: Optional[Dict[str, Any]] = None


class MessageUpdate(BaseModel):
    """Update existing message."""
    content: str = Field(..., min_length=1, max_length=10000)


class CodeSnippet(BaseModel):
    """Code snippet in a message."""
    language: str
    code: str
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None


class MessageResponse(BaseModel):
    """Message response model."""
    id: int
    session_id: int
    user_id: Optional[int]
    role: MessageRole
    content: str
    code_snippets: List[CodeSnippet] = []
    referenced_files: List[str] = []
    referenced_chunks: List[int] = []
    applied_commands: Dict[str, Any] = {}
    is_edited: bool = False
    edited_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatSessionResponse(BaseModel):
    """Chat session response model."""
    id: int
    project_id: int
    title: str
    is_active: bool
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    message_count: Optional[int] = 0

    class Config:
        from_attributes = True


class ChatSessionListResponse(BaseModel):
    """List of chat sessions."""
    items: List[ChatSessionResponse]
    total: int
```

#### 2. Router Endpoints

`backend/app/routers/chat.py` (≤300 lines):
```python
"""Chat API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session
from typing import List, Optional

from app.dependencies import DatabaseDep, CurrentUserRequired
from app.models.chat import ChatSession, ChatMessage
from app.schemas.chat import (
    ChatSessionCreate, ChatSessionUpdate, ChatSessionResponse,
    ChatSessionListResponse, MessageResponse
)
from app.services.chat_service import ChatService
from app.websocket.handlers import handle_chat_connection
from app.auth.utils import get_current_user_ws

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/sessions", response_model=ChatSessionListResponse)
async def list_sessions(
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    project_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0)
):
    """List chat sessions with optional filtering."""
    query = db.query(ChatSession)

    if project_id:
        query = query.filter(ChatSession.project_id == project_id)
    if is_active is not None:
        query = query.filter(ChatSession.is_active == is_active)

    total = query.count()
    sessions = query.offset(offset).limit(limit).all()

    # Add message count
    items = []
    for session in sessions:
        response = ChatSessionResponse.from_orm(session)
        response.message_count = db.query(ChatMessage).filter_by(
            session_id=session.id, is_deleted=False
        ).count()
        items.append(response)

    return ChatSessionListResponse(items=items, total=total)


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_session(
    session_data: ChatSessionCreate,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Create a new chat session."""
    service = ChatService(db)
    session = await service.create_session(
        project_id=session_data.project_id,
        title=session_data.title
    )
    return ChatSessionResponse.from_orm(session)


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session(
    session_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Get chat session details."""
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    response = ChatSessionResponse.from_orm(session)
    response.message_count = db.query(ChatMessage).filter_by(
        session_id=session.id, is_deleted=False
    ).count()

    return response


@router.patch("/sessions/{session_id}", response_model=ChatSessionResponse)
async def update_session(
    session_id: int,
    update_data: ChatSessionUpdate,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Update chat session."""
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    if update_data.title is not None:
        session.title = update_data.title
    if update_data.is_active is not None:
        session.is_active = update_data.is_active

    db.commit()
    return ChatSessionResponse.from_orm(session)


@router.delete("/sessions/{session_id}", status_code=204)
async def delete_session(
    session_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep
):
    """Delete a chat session."""
    session = db.query(ChatSession).filter_by(id=session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db.delete(session)
    db.commit()


@router.get("/sessions/{session_id}/messages", response_model=List[MessageResponse])
async def get_messages(
    session_id: int,
    current_user: CurrentUserRequired,
    db: DatabaseDep,
    limit: int = Query(50, ge=1, le=100),
    before_id: Optional[int] = None
):
    """Get messages for a chat session."""
    service = ChatService(db)
    messages = service.get_session_messages(session_id, limit, before_id)
    return [MessageResponse.from_orm(msg) for msg in messages]


@router.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    session_id: int,
    db: DatabaseDep
):
    """WebSocket endpoint for real-time chat."""
    # Authenticate WebSocket connection
    try:
        token = websocket.query_params.get("token")
        if not token:
            await websocket.close(code=1008, reason="Missing token")
            return

        current_user = await get_current_user_ws(websocket, token, db)
        if not current_user:
            await websocket.close(code=1008, reason="Invalid token")
            return

        # Handle chat connection
        await handle_chat_connection(websocket, session_id, current_user, db)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.close(code=1011, reason=str(e))
```

#### 3. WebSocket Authentication

`backend/app/auth/utils.py` (add to existing file):
```python
async def get_current_user_ws(
    websocket: WebSocket,
    token: str,
    db: Session
) -> Optional[User]:
    """Authenticate WebSocket connection."""
    try:
        payload = security.decode_access_token(token)
        user_id = security.token_sub_identity(payload)
        user = db.get(User, user_id)

        if not user or not user.is_active:
            return None

        return user
    except Exception:
        return None
```

#### 4. Database Migration

`backend/alembic/versions/003_add_chat_tables.py`:
```python
"""Add chat tables

Revision ID: 003
Revises: 002
Create Date: 2024-01-20
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = '003'
down_revision = '002'
branch_labels = None
depends_on = None


def upgrade():
    # Create chat_sessions table
    op.create_table('chat_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('project_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=200), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('summary_updated_at', sa.DateTime(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['project_id'], ['projects.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_session_project', 'chat_sessions', ['project_id'])
    op.create_index('idx_chat_session_updated', 'chat_sessions', ['updated_at'])

    # Create chat_messages table
    op.create_table('chat_messages',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('role', sa.String(length=20), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('code_snippets', sa.JSON(), nullable=True),
        sa.Column('referenced_files', sa.JSON(), nullable=True),
        sa.Column('referenced_chunks', sa.JSON(), nullable=True),
        sa.Column('applied_commands', sa.JSON(), nullable=True),
        sa.Column('is_edited', sa.Boolean(), nullable=True, default=False),
        sa.Column('edited_at', sa.DateTime(), nullable=True),
        sa.Column('original_content', sa.Text(), nullable=True),
        sa.Column('is_deleted', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['session_id'], ['chat_sessions.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_chat_message_session', 'chat_messages', ['session_id'])
    op.create_index('idx_chat_message_created', 'chat_messages', ['created_at'])


def downgrade():
    op.drop_index('idx_chat_message_created', table_name='chat_messages')
    op.drop_index('idx_chat_message_session', table_name='chat_messages')
    op.drop_table('chat_messages')
    op.drop_index('idx_chat_session_updated', table_name='chat_sessions')
    op.drop_index('idx_chat_session_project', table_name='chat_sessions')
    op.drop_table('chat_sessions')
```

### Essential Frontend Components

#### 5. MessageList Component

`frontend/src/components/chat/MessageList.jsx` (≤300 lines):
```jsx
import React, { useEffect, useRef, useState } from 'react';
import { formatDistanceToNow } from 'date-fns';
import CodeSnippet from '../search/CodeSnippet';

export default function MessageList({
  messages,
  onMessageSelect,
  onCodeSelect,
  onMessageEdit,
  onMessageDelete,
  currentUserId
}) {
  const bottomRef = useRef(null);
  const [editingId, setEditingId] = useState(null);
  const [editContent, setEditContent] = useState('');

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleEdit = (message) => {
    setEditingId(message.id);
    setEditContent(message.content);
  };

  const handleSaveEdit = () => {
    if (editingId && editContent.trim()) {
      onMessageEdit(editingId, editContent);
      setEditingId(null);
      setEditContent('');
    }
  };

  const handleCancelEdit = () => {
    setEditingId(null);
    setEditContent('');
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${
            message.role === 'assistant' ? 'justify-start' : 'justify-end'
          }`}
        >
          <div
            className={`max-w-[70%] rounded-lg p-4 ${
              message.role === 'assistant'
                ? 'bg-gray-100 text-gray-900'
                : 'bg-blue-500 text-white'
            } ${onMessageSelect ? 'cursor-pointer hover:opacity-90' : ''}`}
            onClick={() => onMessageSelect?.(message)}
          >
            {/* Message header */}
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs opacity-70">
                {message.role === 'assistant' ? 'AI' : 'You'}
              </span>
              <div className="flex items-center space-x-2">
                <span className="text-xs opacity-70">
                  {formatDistanceToNow(new Date(message.created_at), {
                    addSuffix: true
                  })}
                </span>
                {message.is_edited && (
                  <span className="text-xs opacity-70">(edited)</span>
                )}
              </div>
            </div>

            {/* Message content */}
            {editingId === message.id ? (
              <div className="space-y-2">
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full p-2 rounded border text-gray-900"
                  rows={4}
                />
                <div className="flex space-x-2">
                  <button
                    onClick={handleSaveEdit}
                    className="px-3 py-1 bg-green-500 text-white rounded text-sm"
                  >
                    Save
                  </button>
                  <button
                    onClick={handleCancelEdit}
                    className="px-3 py-1 bg-gray-500 text-white rounded text-sm"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="prose prose-sm max-w-none">
                {message.content}
              </div>
            )}

            {/* Code snippets */}
            {message.code_snippets?.length > 0 && (
              <div className="mt-4 space-y-2">
                {message.code_snippets.map((snippet, index) => (
                  <div key={index} className="relative">
                    <CodeSnippet
                      content={snippet.code}
                      language={snippet.language}
                      startLine={snippet.line_start || 1}
                    />
                    {onCodeSelect && (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          onCodeSelect(snippet);
                        }}
                        className="absolute top-2 right-2 px-2 py-1 bg-blue-500 text-white text-xs rounded"
                      >
                        Use Code
                      </button>
                    )}
                  </div>
                ))}
              </div>
            )}

            {/* Referenced files */}
            {message.referenced_files?.length > 0 && (
              <div className="mt-2 flex flex-wrap gap-1">
                {message.referenced_files.map((file, index) => (
                  <span
                    key={index}
                    className="text-xs bg-gray-200 text-gray-700 px-2 py-1 rounded"
                  >
                    {file}
                  </span>
                ))}
              </div>
            )}

            {/* Actions */}
            {message.user_id === currentUserId && message.role === 'user' && (
              <div className="mt-2 flex space-x-2">
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleEdit(message);
                  }}
                  className="text-xs opacity-70 hover:opacity-100"
                >
                  Edit
                </button>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    onMessageDelete(message.id);
                  }}
                  className="text-xs opacity-70 hover:opacity-100"
                >
                  Delete
                </button>
              </div>
            )}
          </div>
        </div>
      ))}
      <div ref={bottomRef} />
    </div>
  );
}
```

#### 6. CodePreview Component

`frontend/src/components/chat/CodePreview.jsx` (≤200 lines):
```jsx
import React from 'react';
import { Light as SyntaxHighlighter } from 'react-syntax-highlighter';
import { atomOneDark } from 'react-syntax-highlighter/dist/esm/styles/hljs';

export default function CodePreview({ snippets, onApply }) {
  if (!snippets || snippets.length === 0) return null;

  return (
    <div className="border-t border-gray-200 bg-gray-50 p-4">
      <h3 className="text-sm font-medium text-gray-900 mb-3">
        Code Suggestions
      </h3>

      <div className="space-y-3 max-h-64 overflow-y-auto">
        {snippets.map((snippet, index) => (
          <div key={index} className="bg-white rounded border border-gray-200">
            <div className="flex items-center justify-between px-3 py-2 border-b border-gray-200">
              <span className="text-xs font-medium text-gray-600">
                {snippet.language}
              </span>
              {onApply && (
                <button
                  onClick={() => onApply(snippet.code)}
                  className="text-xs bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600"
                >
                  Apply to Editor
                </button>
              )}
            </div>

            <div className="p-2">
              <SyntaxHighlighter
                language={snippet.language}
                style={atomOneDark}
                customStyle={{
                  margin: 0,
                  padding: '0.5rem',
                  fontSize: '0.75rem',
                  maxHeight: '150px',
                  overflow: 'auto'
                }}
              >
                {snippet.code}
              </SyntaxHighlighter>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
```

### Configuration Updates

#### 7. Environment Variables

Add to `.env.example`:
```bash
# LLM Configuration
OPENAI_API_KEY=your-openai-api-key
AZURE_OPENAI_API_KEY=your-azure-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
LLM_PROVIDER=openai  # or 'azure'
LLM_MODEL=gpt-4
MAX_CONTEXT_TOKENS=8000

# WebSocket Configuration
WEBSOCKET_PING_INTERVAL=30
WEBSOCKET_PING_TIMEOUT=10
```

#### 8. Config Updates

`backend/app/config.py` (add to existing):
```python
# LLM settings
llm_provider: str = "openai"
llm_model: str = "gpt-4"
max_context_tokens: int = 8000

# WebSocket settings
websocket_ping_interval: int = 30
websocket_ping_timeout: int = 10
```

#### 9. Requirements Update

Add to `backend/requirements.txt`:
```
# LLM dependencies
openai==1.12.0
tiktoken==0.5.2
tenacity==8.2.3
```

Add to `frontend/package.json`:
```json
"@monaco-editor/react": "^4.6.0",
"date-fns": "^3.3.1"
```

### Simple Test Example

`backend/tests/test_chat.py` (≤200 lines):
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_create_chat_session(test_user_token, test_project):
    """Test creating a chat session."""
    response = client.post(
        "/api/chat/sessions",
        json={"project_id": test_project.id, "title": "Test Chat"},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Chat"
    assert data["project_id"] == test_project.id
    assert data["is_active"] is True


def test_list_sessions(test_user_token, test_project):
    """Test listing chat sessions."""
    # Create a session first
    client.post(
        "/api/chat/sessions",
        json={"project_id": test_project.id},
        headers={"Authorization": f"Bearer {test_user_token}"}
    )

    response = client.get(
        f"/api/chat/sessions?project_id={test_project.id}",
        headers={"Authorization": f"Bearer {test_user_token}"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1
```

## Summary

This completes the essential missing components for Phase 5:

✅ **Backend Components**:
- Pydantic schemas for validation
- Complete router endpoints
- WebSocket authentication
- Database migrations
- Basic configuration

✅ **Frontend Components**:
- MessageList component
- CodePreview component
- Required dependencies

✅ **Configuration**:
- Environment variables
- Updated requirements

The implementation focuses on **essential functionality** without over-engineering:
- No complex background task system (uses FastAPI's built-in)
- Simple rate limiting (can use slowapi if needed)
- Basic error handling
- No extensive monitoring/observability

This provides a functional chat system that can be enhanced incrementally based on actual usage needs.
