# Unified AI Configuration API

The Unified AI Configuration API provides a centralized interface for managing all AI model settings, generation parameters, and reasoning configurations.

## Overview

- **Base URL**: `/api/v1/ai-config`
- **Authentication**: Required for all endpoints
- **Response Format**: All responses use camelCase field names
- **Input Format**: Accepts both camelCase and snake_case field names
- **Auto-Seeding**: Model catalog is automatically seeded on first startup

## Key Features

- **Single Source of Truth**: All AI configuration managed through unified endpoints
- **Flexible Input**: Accepts both camelCase and snake_case input field names
- **Consistent Output**: Always returns camelCase field names in responses
- **Real-time Updates**: WebSocket notifications for configuration changes
- **Model Catalog**: Comprehensive model information with capabilities and costs
- **Configuration Validation**: Built-in validation and testing
- **Preset Management**: Predefined configuration presets

## Endpoints

### GET /api/v1/ai-config

Get current AI configuration including all settings and available models.

**Response:**
```json
{
  "current": {
    "provider": "openai",
    "modelId": "gpt-4o",
    "temperature": 0.7,
    "maxTokens": 2048,
    "topP": 1.0,
    "frequencyPenalty": 0.0,
    "presencePenalty": 0.0,
    "enableReasoning": false,
    "reasoningEffort": "medium",
    "claudeExtendedThinking": true,
    "claudeThinkingMode": "enabled",
    "claudeThinkingBudgetTokens": 16384,
    "useResponsesApi": false,
    "createdAt": "2025-07-07T21:00:00Z",
    "updatedAt": "2025-07-07T21:30:00Z"
  },
  "availableModels": [
    {
      "modelId": "gpt-4o",
      "displayName": "GPT-4 Omni",
      "provider": "openai",
      "modelFamily": "gpt-4",
      "capabilities": {
        "supportsFunctions": true,
        "supportsVision": true,
        "supportsReasoning": false,
        "supportsStreaming": true,
        "maxContextWindow": 128000,
        "maxOutputTokens": 4096
      },
      "costPer1kInputTokens": 0.0025,
      "costPer1kOutputTokens": 0.01,
      "performanceTier": "balanced",
      "isAvailable": true,
      "isDeprecated": false,
      "recommendedUseCases": ["complex", "code", "creative"]
    }
  ],
  "providers": {
    "openai": {
      "displayName": "OpenAI",
      "models": [...],
      "capabilities": {
        "supportsFunctions": true,
        "supportsStreaming": true,
        "supportsVision": true
      }
    },
    "azure": {
      "displayName": "Azure OpenAI",
      "models": [...],
      "capabilities": {
        "supportsFunctions": true,
        "supportsStreaming": true,
        "supportsResponsesApi": true,
        "supportsReasoning": true
      }
    },
    "anthropic": {
      "displayName": "Anthropic",
      "models": [...],
      "capabilities": {
        "supportsFunctions": true,
        "supportsStreaming": true,
        "supportsThinking": true
      }
    }
  },
  "lastUpdated": "2025-07-07T21:30:00Z"
}
```

### PUT /api/v1/ai-config

Update AI configuration with validation.

**Input Format**: Accepts both camelCase and snake_case field names
```json
{
  "temperature": 0.8,
  "max_tokens": 1024,        // snake_case accepted
  "topP": 0.9,              // camelCase accepted  
  "model_id": "gpt-4o",     // snake_case accepted
  "enable_reasoning": true   // snake_case accepted
}
```

**Response**: Always returns camelCase field names
```json
{
  "provider": "openai",
  "modelId": "gpt-4o",
  "temperature": 0.8,
  "maxTokens": 1024,
  "topP": 0.9,
  "enableReasoning": true,
  "updatedAt": "2025-07-07T21:35:00Z"
}
```

### GET /api/v1/ai-config/defaults

Return the canonical default provider / model / generation parameters.

**Response**:
```json
{
  "provider": "openai",
  "modelId": "gpt-4o-mini",
  "temperature": 0.7,
  "maxTokens": null,
  "topP": 1.0,
  "frequencyPenalty": 0.0,
  "presencePenalty": 0.0,
  "enableReasoning": true,
  "reasoningEffort": "medium",
  "claudeExtendedThinking": false,
  "claudeThinkingMode": "off",
  "claudeThinkingBudgetTokens": 8192,
  "useResponsesApi": false
}
```

### POST /api/v1/ai-config/test

Test AI configuration with actual API call.

**Request:**
```json
{
  "provider": "openai",
  "modelId": "gpt-4o",
  "temperature": 0.7,
  "maxTokens": 100
}
```

**Response:**
```json
{
  "success": true,
  "message": "Configuration test successful",
  "responseTime": 1.23,
  "model": "gpt-4o",
  "provider": "openai"
}
```

### GET /api/v1/ai-config/models

Get list of available AI models.

**Query Parameters:**
- `provider` (optional): Filter by provider (openai, azure, anthropic)
- `include_deprecated` (optional): Include deprecated models (default: false)

**Response:**
```json
[
  {
    "modelId": "gpt-4o",
    "displayName": "GPT-4 Omni",
    "provider": "openai",
    "modelFamily": "gpt-4",
    "capabilities": {
      "supportsFunctions": true,
      "supportsVision": true,
      "maxContextWindow": 128000,
      "maxOutputTokens": 4096
    },
    "costPer1kInputTokens": 0.0025,
    "costPer1kOutputTokens": 0.01,
    "performanceTier": "balanced",
    "averageLatencyMs": 2500,
    "isAvailable": true,
    "isDeprecated": false,
    "recommendedUseCases": ["complex", "code", "creative"]
  }
]
```

### GET /api/v1/ai-config/models/{model_id}

Get detailed information for a specific model.

**Response:**
```json
{
  "modelId": "gpt-4o",
  "displayName": "GPT-4 Omni",
  "provider": "openai",
  "modelFamily": "gpt-4",
  "capabilities": {
    "supportsFunctions": true,
    "supportsVision": true,
    "supportsReasoning": false,
    "supportsStreaming": true,
    "supportsJsonMode": true,
    "maxContextWindow": 128000,
    "maxOutputTokens": 4096,
    "supportsParallelTools": true
  },
  "costPer1kInputTokens": 0.0025,
  "costPer1kOutputTokens": 0.01,
  "performanceTier": "balanced",
  "averageLatencyMs": 2500,
  "isAvailable": true,
  "isDeprecated": false,
  "deprecationDate": null,
  "recommendedUseCases": ["complex", "code", "creative"]
}
```

### POST /api/v1/ai-config/validate

Validate configuration without saving.

**Request:**
```json
{
  "provider": "openai",
  "modelId": "gpt-4o",
  "temperature": 0.7,
  "maxTokens": 2048
}
```

**Response:**
```json
{
  "valid": true,
  "error": null,
  "validatedAt": "2025-07-07T21:40:00Z"
}
```

**Error Response:**
```json
{
  "valid": false,
  "error": "Temperature must be between 0.0 and 2.0",
  "validatedAt": "2025-07-07T21:40:00Z"
}
```

### GET /api/v1/ai-config/presets

Get predefined configuration presets.

**Response:**
```json
[
  {
    "id": "balanced",
    "name": "Balanced",
    "description": "Good balance of quality and speed",
    "config": {
      "temperature": 0.7,
      "maxTokens": 2048,
      "topP": 0.95,
      "reasoningEffort": "medium"
    }
  },
  {
    "id": "creative",
    "name": "Creative",
    "description": "More creative and varied responses",
    "config": {
      "temperature": 1.2,
      "maxTokens": 3000,
      "topP": 0.95,
      "frequencyPenalty": 0.2,
      "presencePenalty": 0.2,
      "reasoningEffort": "high"
    }
  },
  {
    "id": "precise",
    "name": "Precise",
    "description": "Focused and deterministic responses",
    "config": {
      "temperature": 0.3,
      "maxTokens": 2048,
      "topP": 0.9,
      "reasoningEffort": "high"
    }
  }
]
```

## Configuration Fields

### Generation Parameters

| Field | Type | Range | Description |
|-------|------|-------|-------------|
| `temperature` | float | 0.0-2.0 | Controls randomness in generation |
| `maxTokens` | integer | 1-128000 | Maximum tokens to generate |
| `topP` | float | 0.0-1.0 | Nucleus sampling parameter |
| `frequencyPenalty` | float | -2.0-2.0 | Penalty for token frequency |
| `presencePenalty` | float | -2.0-2.0 | Penalty for token presence |
| `stopSequences` | array | - | Sequences where generation stops |
| `seed` | integer | - | Random seed for reproducibility |

### Reasoning Parameters

| Field | Type | Options | Description |
|-------|------|---------|-------------|
| `enableReasoning` | boolean | - | Enable reasoning for supported models |
| `reasoningEffort` | string | low, medium, high | Reasoning effort level (Azure/OpenAI) |
| `claudeExtendedThinking` | boolean | - | Enable Claude's extended thinking |
| `claudeThinkingMode` | string | off, enabled, aggressive | Claude thinking mode |
| `claudeThinkingBudgetTokens` | integer | 1024-65536 | Token budget for Claude thinking |

### Model Selection

| Field | Type | Description |
|-------|------|-------------|
| `provider` | string | AI provider (openai, azure, anthropic) |
| `modelId` | string | Model identifier |
| `useResponsesApi` | boolean | Use Azure Responses API |

## Auto-Seeding Behavior

The unified configuration system automatically seeds the model catalog on first startup when `ENABLE_UNIFIED_CONFIG=true`. This includes:

1. **Default Configuration**: Creates default runtime configuration if none exists
2. **Model Catalog**: Seeds available models with capabilities and cost information  
3. **Provider Information**: Sets up provider capabilities and supported features

The seeding process runs during application startup and is idempotent - it won't overwrite existing configuration.

## Field Name Compatibility

### Input (Accepts Both)
The API accepts both camelCase and snake_case field names in requests:

```json
{
  "max_tokens": 2048,     // snake_case
  "maxTokens": 2048,      // camelCase
  "top_p": 0.9,          // snake_case
  "topP": 0.9,           // camelCase
  "model_id": "gpt-4o",  // snake_case
  "modelId": "gpt-4o"    // camelCase
}
```

### Output (Always camelCase)
All API responses use consistent camelCase field names:

```json
{
  "maxTokens": 2048,     // Always camelCase
  "topP": 0.9,          // Always camelCase
  "modelId": "gpt-4o",  // Always camelCase
  "availableModels": [], // Always camelCase
  "lastUpdated": "..."   // Always camelCase
}
```

## WebSocket Notifications

Configuration changes are broadcast via WebSocket to all connected clients:

```json
{
  "type": "config_update",
  "data": {
    "current": { /* updated configuration */ },
    "availableModels": [ /* model list */ ],
    "timestamp": "2025-07-07T21:45:00Z"
  }
}
```

## Error Responses

All endpoints return consistent error responses:

```json
{
  "detail": "Configuration validation failed",
  "error_code": "VALIDATION_ERROR",
  "errors": [
    {
      "field": "temperature",
      "message": "Temperature must be between 0.0 and 2.0"
    }
  ]
}
```

## Migration from Legacy APIs

The unified configuration API replaces the following legacy endpoints:

- `/api/config` → `/api/v1/ai-config`
- `/api/v1/models` → `/api/v1/ai-config/models`
- `/api/thinking-config` → Merged into `/api/v1/ai-config`
- `/api/provider-config` → Merged into `/api/v1/ai-config`

Legacy endpoints will redirect to the unified API with a 301 status code during the transition period.

## Environment Variables

- `ENABLE_UNIFIED_CONFIG=true` - Enable the unified configuration system
- `ENABLE_REASONING=true` - Enable reasoning/thinking capabilities
- Standard provider API keys (OPENAI_API_KEY, AZURE_OPENAI_API_KEY, ANTHROPIC_API_KEY)

## Security Considerations

- All endpoints require authentication
- API keys are stored encrypted in the database
- Configuration changes are logged with user attribution
- Rate limiting applies to all endpoints
- CSRF protection for state-changing operations