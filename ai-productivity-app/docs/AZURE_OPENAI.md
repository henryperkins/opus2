# Azure OpenAI Integration

This application supports both standard OpenAI and Azure OpenAI as LLM providers, with enhanced support for Azure's new Responses API.

## Configuration Options

### 1. Standard OpenAI

```bash
LLM_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
LLM_MODEL=gpt-4o-mini
```

### 2. Azure OpenAI - Chat Completions API

Traditional Azure OpenAI integration using the Chat Completions API:

```bash
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2024-02-01
LLM_MODEL=gpt-4o  # Your deployment name
```

### 3. Azure OpenAI - Responses API (Recommended)

Enhanced integration using Azure's new Responses API with advanced features:

```bash
LLM_PROVIDER=azure
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=2025-04-01-preview
LLM_MODEL=gpt-4.1  # Your deployment name
```

### 4. Azure OpenAI - Entra ID Authentication

For enhanced security using Azure Active Directory:

```bash
LLM_PROVIDER=azure
AZURE_AUTH_METHOD=entra_id
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_VERSION=preview
LLM_MODEL=gpt-4.1
```

## Azure Responses API Features

When using `AZURE_OPENAI_API_VERSION=preview`, the application automatically enables the Responses API, which provides:

### Advanced Models
- `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano` - Latest reasoning models
- `o3`, `o4-mini` - Advanced reasoning models
- `gpt-image-1` - Image generation
- `computer-use-preview` - Computer interaction capabilities

### Enhanced Capabilities
- **Background Tasks**: Long-running tasks processed asynchronously
- **Image Generation**: Built-in image creation and editing
- **Computer Use**: Automated computer interaction (Playwright integration)
- **MCP Servers**: Model Context Protocol for external tool integration
- **Multi-turn Conversations**: Stateful conversations with response chaining
- **Streaming**: Real-time response streaming with partial results

### API Differences

The Responses API uses a different message format:

**Chat Completions API:**
```python
{
    "model": "gpt-4o",
    "messages": [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "Hello"}
    ]
}
```

**Responses API:**
```python
{
    "model": "gpt-4.1",
    "instructions": "You are a helpful assistant",  # System message
    "input": [
        {"role": "user", "content": "Hello"}
    ]
}
```

The LLM client automatically handles this conversion when `use_responses_api=True`.

## Authentication Methods

### API Key Authentication
Standard authentication using an API key:
```bash
AZURE_OPENAI_API_KEY=your-api-key
```

### Azure Active Directory (Entra ID)
Enhanced security using managed identity or service principal:
```bash
AZURE_AUTH_METHOD=entra_id
# No API key needed - uses DefaultAzureCredential
```

Requires the `azure-identity` package (included in requirements.txt).

## Model Availability

Different models are available depending on your Azure OpenAI deployment:

### Standard Models (Chat Completions API)
- `gpt-4o`, `gpt-4o-mini`
- `gpt-4-turbo`, `gpt-4`
- `gpt-35-turbo` (Azure naming)

### Advanced Models (Responses API)
- `gpt-4.1`, `gpt-4.1-mini`, `gpt-4.1-nano`
- `o3`, `o4-mini`
- `gpt-image-1`
- `computer-use-preview`

## Error Handling

The client includes intelligent fallback logic:
1. Attempts to use the configured model
2. If model access is denied, falls back to `gpt-4o-mini`
3. Logs detailed error information for debugging

Common errors:
- **Project access denied**: Your Azure project doesn't have access to the requested model
- **Deployment not found**: The deployment name doesn't exist in your resource
- **Authentication failed**: Invalid API key or Azure credentials

## Best Practices

1. **Use Responses API for new deployments** - Enable advanced features
2. **Configure model fallbacks** - Ensure `gpt-4o-mini` is available as a fallback
3. **Use Entra ID authentication** - More secure than API keys
4. **Monitor token usage** - Responses API provides detailed usage statistics
5. **Enable background mode** - For long-running reasoning tasks

## Troubleshooting

### Model Access Issues
```
Error: Project 'proj_xxx' does not have access to model 'gpt-3.5-turbo'
```
Solution: Enable the model in your Azure OpenAI project settings or update the `LLM_MODEL` configuration.

### Authentication Failures
```
Error: Azure OpenAI requires either api_key or azure-identity package
```
Solution: Install `azure-identity` or provide `AZURE_OPENAI_API_KEY`.

### API Version Compatibility
```
Error: No overloads for "create" match the provided arguments
```
Solution: Ensure you're using the correct `AZURE_OPENAI_API_VERSION` for your chosen features.

## Migration Guide

### From OpenAI to Azure OpenAI
1. Set up Azure OpenAI resource
2. Create model deployments
3. Update environment variables:
   ```bash
   LLM_PROVIDER=azure
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
   AZURE_OPENAI_API_KEY=your-key
   LLM_MODEL=your-deployment-name
   ```

### From Chat Completions to Responses API
1. Update API version:
   ```bash
   AZURE_OPENAI_API_VERSION=preview
   ```
2. Deploy advanced models (gpt-4.1, o3, etc.)
3. Update model configuration:
   ```bash
   LLM_MODEL=gpt-4.1
   ```

The application automatically detects and uses the appropriate API based on your configuration.

## Frontend Integration

The frontend automatically detects and displays the current Azure OpenAI configuration:

### Provider Status Display

**Header Status**: A compact status indicator in the application header shows:
- Current provider (OpenAI vs Azure OpenAI)
- Active model name
- Responses API status (if Azure)

**Settings Page**: Detailed provider information in Settings > AI Provider Configuration:
- Provider and model details
- Available features and their status
- List of available models
- API type and capabilities

### Configuration Endpoint

The frontend fetches provider information from `/api/config`:
- Available providers and models
- Current active configuration
- Feature flags and capabilities
- API version support

No frontend configuration changes are needed when switching between OpenAI and Azure OpenAI.
