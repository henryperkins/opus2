# Complete Integration Guide - Phase 1, 2, and 3

## Overview
This guide covers the complete integration of all three phases:
- **Phase 1**: Knowledge Base Integration
- **Phase 2**: Model Configuration
- **Phase 3**: Enhanced Response Rendering

## File Structure

```
frontend/src/
├── components/
│   ├── knowledge/          # Phase 1
│   │   ├── KnowledgeContextPanel.tsx
│   │   ├── SmartKnowledgeSearch.tsx
│   │   └── KnowledgeAssistant.tsx
│   ├── chat/              # All Phases
│   │   ├── CitationRenderer.tsx         # Phase 1
│   │   ├── EnhancedCommandInput.tsx     # Phase 1
│   │   ├── ModelSwitcher.tsx            # Phase 2
│   │   ├── StreamingMessage.tsx         # Phase 3
│   │   ├── RichMessageRenderer.tsx      # Phase 3
│   │   ├── InteractiveElements.tsx      # Phase 3
│   │   └── ResponseTransformer.tsx      # Phase 3
│   ├── settings/          # Phase 2
│   │   ├── ModelConfiguration.tsx
│   │   └── PromptManager.tsx
│   └── analytics/         # Phase 3
│       └── ResponseQuality.tsx
├── hooks/
│   ├── useKnowledgeContext.ts    # Phase 1
│   └── useModelSelection.ts      # Phase 2
├── api/
│   ├── search.ts                 # Phase 1
│   └── config.ts                 # Phase 2
├── types/
│   └── knowledge.ts              # Phase 1
├── commands/
│   └── knowledge-commands.ts     # Phase 1
└── pages/
    └── EnhancedChatPage.tsx      # Complete Integration

backend/
├── app/
│   ├── routers/
│   │   ├── config.py      # Model configuration endpoints
│   │   └── search.py      # Knowledge search endpoints
│   └── services/
│       ├── knowledge_service.py
│       └── model_service.py
```

## Phase 1: Knowledge Integration

### 1.1 Backend Setup

Create search endpoints in `backend/app/routers/search.py`:

```python
from fastapi import APIRouter, Depends
from app.search.hybrid import HybridSearch
from app.schemas.search import SearchRequest, SearchResponse

router = APIRouter(prefix="/api/search")

@router.post("/documents")
async def search_documents(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    # Implement document search
    pass

@router.post("/code")
async def search_code(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    # Implement code search
    pass

@router.post("/hybrid")
async def hybrid_search(
    request: SearchRequest,
    db: Session = Depends(get_db)
):
    # Implement hybrid search
    pass
```

### 1.2 Frontend Integration

1. **Add Knowledge Context to Chat**:
```tsx
// In your existing chat page
import { useKnowledgeChat } from '../hooks/useKnowledgeContext';

const knowledgeChat = useKnowledgeChat(projectId);

// Update message sending
const handleSendMessage = async (content: string, metadata: any) => {
  // Knowledge context is automatically included
  const enhanced = knowledgeChat.buildEnhancedMessage(content);
  await sendMessage(enhanced.message, enhanced.metadata);
};
```

2. **Add Knowledge Commands**:
```tsx
// Commands are automatically registered in EnhancedCommandInput
// Users can type:
// /find-similar
// /cite "search query"
// /cross-reference topic
// /knowledge-summary
```

## Phase 2: Model Configuration

### 2.1 Backend Configuration

Update `backend/app/routers/config.py`:

```python
@router.put("/model")
async def update_model_config(
    config: ModelConfigUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Save user's model preferences
    pass

@router.post("/test")
async def test_model_config(
    config: ModelConfigTest,
    current_user: User = Depends(get_current_user)
):
    # Test model configuration
    pass

@router.get("/models/{model}/stats")
async def get_model_stats(
    model: str,
    current_user: User = Depends(get_current_user)
):
    # Return model usage statistics
    pass
```

### 2.2 Settings Page Integration

Add to your settings page:

```tsx
import ModelConfiguration from '../components/settings/ModelConfiguration';
import PromptManager from '../components/settings/PromptManager';

<Tabs>
  <TabPanel label="AI Configuration">
    <ModelConfiguration />
  </TabPanel>
  <TabPanel label="Prompt Templates">
    <PromptManager />
  </TabPanel>
</Tabs>
```

### 2.3 Chat Integration

The model switcher is automatically integrated in the enhanced chat page header.

## Phase 3: Response Rendering

### 3.1 Enhanced Message Rendering

Replace your existing message rendering:

```tsx
// Before
<div>{message.content}</div>

// After
<RichMessageRenderer
  content={message.content}
  metadata={message.metadata}
  onCodeRun={handleCodeRun}
  onCodeApply={handleCodeApply}
/>
```

### 3.2 Streaming Support

Update your WebSocket handler:

```tsx
// Handle streaming messages
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  if (data.type === 'ai_stream') {
    handleStreamingUpdate(data.message_id, data.content, data.done);
  }
};
```

### 3.3 Interactive Elements

Add support for interactive responses:

```tsx
// In message metadata
{
  interactiveElements: [
    {
      id: 'code-1',
      type: 'code',
      data: { code: '...', language: 'python' },
      onInteraction: async (action, data) => {
        // Handle code execution
      }
    }
  ]
}
```

## Complete Integration Steps

### Step 1: Update Dependencies

```bash
npm install framer-motion recharts react-markdown remark-gfm remark-math rehype-katex mermaid katex
```

### Step 2: Update Your Chat Page

Replace your existing chat page with `EnhancedChatPage.tsx` or integrate its features:

```tsx
import EnhancedChatPage from './pages/EnhancedChatPage';

// In your router
<Route path="/projects/:projectId/chat" element={<EnhancedChatPage />} />
```

### Step 3: Configure Backend

Add required environment variables:

```env
# Model Configuration
OPENAI_API_KEY=your-key
AZURE_OPENAI_API_KEY=your-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com

# Knowledge Base
EMBEDDING_MODEL=text-embedding-3-small
VECTOR_DB_PATH=./data/vectors.db
```

### Step 4: Database Migrations

Add new tables for prompt templates and model preferences:

```sql
-- Prompt templates
CREATE TABLE prompt_templates (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    name VARCHAR(255),
    description TEXT,
    category VARCHAR(100),
    system_prompt TEXT,
    user_prompt_template TEXT,
    variables JSON,
    model_preferences JSON,
    is_public BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);

-- User model preferences
CREATE TABLE user_model_preferences (
    user_id INTEGER PRIMARY KEY,
    provider VARCHAR(50),
    model VARCHAR(100),
    temperature FLOAT,
    max_tokens INTEGER,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

## Usage Examples

### Example 1: Knowledge-Enhanced Chat

```tsx
// User types a message
"How does the authentication system work?"

// System automatically:
1. Searches knowledge base for relevant docs
2. Displays relevant context in Knowledge Panel
3. Includes citations in response
4. Shows confidence score
```

### Example 2: Model Configuration

```tsx
// User wants faster responses
1. Click Model Switcher
2. Select "GPT-3.5 Turbo" for speed
3. System automatically switches
4. Shows performance metrics
```

### Example 3: Interactive Code Response

```tsx
// AI generates code
// User sees:
- Syntax highlighted code
- "Run" button for testing
- "Apply to Editor" button
- Copy button

// User clicks "Run"
// Code executes in sandbox
// Results display inline
```

## Performance Optimization

1. **Lazy Load Heavy Components**:
```tsx
const MermaidDiagram = lazy(() => import('./MermaidDiagram'));
const ChartRenderer = lazy(() => import('./ChartRenderer'));
```

2. **Cache Knowledge Search Results**:
```tsx
const searchCache = new Map();
// Cache for 5 minutes
```

3. **Debounce Real-time Features**:
```tsx
const debouncedSearch = useDebounce(searchQuery, 300);
const debouncedTyping = useDebounce(isTyping, 1000);
```

## Troubleshooting

### Common Issues

1. **Knowledge search not working**
   - Check search API endpoints are implemented
   - Verify embeddings are generated for documents
   - Check vector database connection

2. **Model switching fails**
   - Verify API keys are configured
   - Check model names match provider's naming
   - Ensure fallback models are available

3. **Streaming not working**
   - Check WebSocket connection
   - Verify streaming handler is implemented
   - Check for CORS issues

### Debug Mode

Enable debug logging:
```typescript
localStorage.setItem('chat_debug', 'true');
localStorage.setItem('knowledge_debug', 'true');
localStorage.setItem('model_debug', 'true');
```

## Next Steps

1. **Add Custom Integrations**:
   - GitHub integration for code context
   - Jira integration for issue tracking
   - Slack integration for notifications

2. **Enhance Analytics**:
   - Export chat analytics
   - Model performance dashboards
   - Knowledge base effectiveness metrics

3. **Advanced Features**:
   - Multi-modal support (images, diagrams)
   - Voice input/output
   - Collaborative editing

## Support

For issues or questions:
1. Check component PropTypes for API documentation
2. Enable debug mode for detailed logging
3. Review the example implementation in `EnhancedChatPage.tsx`
