# Chat Flows Integration

## Overview

The `useChatFlows.js` hook provides a comprehensive integration layer for the three key chat flows in the AI Productivity App:

1. **Knowledge Base Flow** - Handles knowledge retrieval and context building
2. **Model Selection Flow** - Manages dynamic model switching and configuration
3. **Response Rendering Flow** - Processes and renders chat responses with interactive elements

## Architecture

### API Integration

The hook integrates with four main API modules:

- **`knowledgeAPI`** - Knowledge base operations and context retrieval
- **`modelsAPI`** - Model configuration and switching
- **`renderingAPI`** - Response processing and interactive element injection
- **`analyticsAPI`** - Metrics tracking and performance monitoring

### State Management

```javascript
const [flowState, setFlowState] = useState({
    knowledgeBase: { step: null, data: null, loading: false },
    modelSelection: { step: null, data: null, loading: false },
    responseRendering: { step: null, data: null, loading: false }
});
```

### Metrics Tracking

Real-time metrics are tracked for:
- Total requests
- Successful requests
- Average response time
- Knowledge hit rate

## Key Features

### 1. Knowledge Base Flow (`executeKnowledgeFlow`)

- **Context Building**: Retrieves relevant knowledge base entries
- **Similarity Search**: Finds semantically similar content
- **Context Optimization**: Builds optimized context for model input
- **Metrics Tracking**: Tracks knowledge retrieval success rates

### 2. Model Selection Flow (`executeModelFlow`)

- **Dynamic Switching**: Changes models based on context and requirements
- **Configuration Management**: Applies model-specific settings
- **Performance Monitoring**: Tracks model performance metrics
- **Fallback Handling**: Provides graceful degradation for model failures

### 3. Response Rendering Flow (`executeRenderingFlow`)

- **Progressive Rendering**: Streams responses in real-time
- **Format Detection**: Automatically detects content formats (markdown, code, etc.)
- **Interactive Elements**: Injects interactive components (code blocks, decision trees, etc.)
- **Action Binding**: Binds user actions to interactive elements

## Usage

```javascript
import { useChatFlows } from '../hooks/useChatFlows';

const ChatComponent = () => {
    const {
        flowState,
        metrics,
        executeKnowledgeFlow,
        executeModelFlow,
        executeRenderingFlow,
        resetFlows
    } = useChatFlows(chatSettings);

    // Execute knowledge flow
    const handleKnowledgeQuery = async (query) => {
        const result = await executeKnowledgeFlow({
            query,
            projectId: 'project-123',
            filters: { category: 'technical' }
        });
    };

    // Execute model flow
    const handleModelSwitch = async (modelConfig) => {
        const result = await executeModelFlow({
            modelConfig,
            context: currentContext,
            projectId: 'project-123'
        });
    };

    // Execute rendering flow
    const handleResponseRender = async (response) => {
        const result = await executeRenderingFlow({
            response,
            settings: renderingSettings,
            interactive: true
        });
    };
};
```

## Configuration

The hook uses configuration from `../config/chat-settings.js`:

- **Flow Configurations**: Step definitions and flow logic
- **Default Settings**: Fallback settings for each flow
- **Validation Rules**: Input validation and sanitization

## Error Handling

Each flow includes comprehensive error handling:

- **API Failures**: Graceful degradation with fallback responses
- **Timeout Handling**: Configurable timeouts for each API call
- **Retry Logic**: Automatic retry for transient failures
- **Error Reporting**: Detailed error logging and user feedback

## Performance

### Optimization Features

- **Parallel Processing**: Multiple flows can execute simultaneously
- **Caching**: Results are cached to reduce API calls
- **Progressive Loading**: Large responses are processed in chunks
- **Memory Management**: Automatic cleanup of large data structures

### Metrics

The hook provides real-time performance metrics:

```javascript
const { metrics } = useChatFlows();
// metrics.totalRequests
// metrics.successfulRequests
// metrics.averageResponseTime
// metrics.knowledgeHitRate
```

## Integration Status

✅ **Completed**:
- All three flows fully implemented
- Real API integration (replacing mock functions)
- Comprehensive error handling
- Metrics tracking and analytics
- Progressive rendering and streaming
- Interactive element injection

🔄 **In Progress**:
- Backend API endpoint implementations
- Enhanced caching strategies
- Advanced error recovery

📋 **Future Enhancements**:
- WebSocket integration for real-time features
- Advanced analytics and A/B testing
- Custom flow configuration UI
- Performance optimization tools

## API Endpoints

The hook expects the following backend endpoints:

### Knowledge API
- `POST /api/v1/knowledge/search` - Knowledge base search
- `POST /api/v1/knowledge/context` - Context building
- `GET /api/v1/knowledge/stats/{projectId}` - Knowledge statistics

### Models API
- `GET /api/v1/models/available` - Available models
- `POST /api/v1/models/switch` - Switch model configuration
- `GET /api/v1/models/config/{modelId}` - Model configuration

### Rendering API
- `POST /api/v1/rendering/detect-formats` - Format detection
- `POST /api/v1/rendering/render-chunk` - Chunk rendering
- `POST /api/v1/rendering/inject-interactive` - Interactive elements
- `POST /api/v1/rendering/bind-actions` - Action binding

### Analytics API
- `POST /api/v1/analytics/track-flow` - Flow metrics
- `POST /api/v1/analytics/track-performance` - Performance metrics
- `GET /api/v1/analytics/dashboard/{projectId}` - Analytics dashboard
