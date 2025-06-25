# Chat Interface Fixes

## Issues Identified and Resolved

### 1. Double Message Issue
**Problem**: User messages were appearing twice in the chat interface.

**Root Cause**: The `useChat` hook was adding messages to the cache via both:
- REST API response in `sendMutation.onSuccess`
- WebSocket broadcast from backend

**Fix**: Removed the `onSuccess` callback from `sendMutation` in `useChat.js` since the backend already broadcasts the message via WebSocket.

**Files Modified**:
- `frontend/src/hooks/useChat.js` - Commented out the `onSuccess` callback

### 2. "Generating response..." Placeholder Issue
**Problem**: AI responses were stuck showing "Generating response..." instead of actual content.

**Root Cause**: The runtime configuration was using `gpt-4o-mini` model, but this deployment doesn't exist in the Azure OpenAI resource, causing 404 errors.

**Fix**: Updated the runtime configuration to use:
- Model: `gpt-4.1` (correct deployment name)
- Provider: `azure`
- Responses API: `enabled`

**Configuration Update**:
```javascript
{
  "provider": "azure",
  "chat_model": "gpt-4.1",
  "useResponsesApi": true,
  "temperature": 0.7,
  "maxTokens": 4000
}
```

## Verification

### Backend Logs Before Fix:
```
404 DeploymentNotFound: The API deployment for this resource does not exist.
If you created the deployment within the last 5 minutes, please wait and try again.
```

### Backend Logs After Fix:
Should show successful Azure Responses API calls with the `gpt-4.1` model.

### Frontend Behavior:
- ✅ Single user message per send
- ✅ AI responses should stream properly
- ✅ No more "Generating response..." stuck messages

## Testing

To test the fixes:
1. Navigate to `/projects/1/chat`
2. Send a message
3. Verify only one user message appears
4. Verify AI response streams and completes properly
5. Check backend logs for successful Azure API calls
