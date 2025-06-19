// frontend/src/components/settings/AIProviderInfo.jsx
import { useState } from 'react';
import { useConfig } from '../../hooks/useConfig';
import { configAPI } from '../../api/config';
import { toast } from '../common/Toast';

const AIProviderInfo = () => {
  const { config, loading, error, refetch } = useConfig();
  const [isEditing, setIsEditing] = useState(false);
  const [selectedModel, setSelectedModel] = useState('');
  const [selectedProvider, setSelectedProvider] = useState('');
  const [saving, setSaving] = useState(false);
  const [validating, setValidating] = useState(false);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-2">
          <div className="h-4 bg-gray-200 rounded w-48 animate-pulse"></div>
          <div className="h-6 bg-gray-200 rounded w-12 animate-pulse"></div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          <div className="flex items-center justify-between">
            <div className="h-3 bg-gray-200 rounded w-16 animate-pulse"></div>
            <div className="h-6 bg-gray-200 rounded w-24 animate-pulse"></div>
          </div>
          <div className="flex items-center justify-between">
            <div className="h-3 bg-gray-200 rounded w-12 animate-pulse"></div>
            <div className="h-6 bg-gray-200 rounded w-32 animate-pulse"></div>
          </div>
          <div className="border-t border-gray-200 pt-3">
            <div className="h-3 bg-gray-200 rounded w-40 mb-2 animate-pulse"></div>
            <div className="flex flex-wrap gap-1">
              {[1,2,3,4].map(i => (
                <div key={i} className="h-6 bg-gray-200 rounded w-16 animate-pulse"></div>
              ))}
            </div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-4">
        <div className="flex items-center">
          <svg className="w-5 h-5 text-red-400 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <div>
            <h3 className="text-sm font-medium text-red-800">Configuration Error</h3>
            <p className="text-sm text-red-600 mt-1">Failed to load AI provider configuration</p>
          </div>
        </div>
        <button
          onClick={() => window.location.reload()}
          className="mt-3 text-sm text-red-600 hover:text-red-800 underline"
        >
          Reload page
        </button>
      </div>
    );
  }

  if (!config) return null;

  const currentProvider = config.current?.provider;
  const currentModel = config.current?.chat_model;
  const isAzure = currentProvider === 'azure';
  const azureFeatures = isAzure ? config.providers?.azure?.features : {};

  const handleEditToggle = () => {
    if (!isEditing) {
      setSelectedProvider(currentProvider);
      setSelectedModel(currentModel);
    }
    setIsEditing(!isEditing);
    setSaveMessage('');
  };

  const validateConfiguration = async () => {
    setValidating(true);
    try {
      const testResponse = await configAPI.testModelConfig({
        provider: selectedProvider,
        chat_model: selectedModel
      });
      if (testResponse.success) {
        toast.success('Configuration validated successfully');
        return true;
      } else {
        toast.error(`Validation failed: ${testResponse.error}`);
        return false;
      }
    } catch (err) {
      toast.error('Failed to validate configuration');
      return false;
    } finally {
      setValidating(false);
    }
  };

  const handleSave = async () => {
    setSaving(true);
    toast.info('Saving configuration...');
    
    try {
      await configAPI.updateModelConfig({
        provider: selectedProvider,
        chat_model: selectedModel
      });
      
      if (refetch) await refetch();
      setIsEditing(false);
      toast.success('Configuration updated successfully!');
    } catch (err) {
      console.error('Failed to update configuration:', err);
      const errorMessage = err.response?.data?.detail || 'Failed to update configuration';
      toast.error(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-sm font-medium text-gray-900">AI Provider Configuration</h3>
          <div className="flex items-center space-x-2">
            {isEditing && (
              <button
                onClick={validateConfiguration}
                disabled={validating || selectedModel === currentModel && selectedProvider === currentProvider}
                className="text-xs px-2 py-1 bg-yellow-600 text-white rounded hover:bg-yellow-700 disabled:opacity-50"
              >
                {validating ? 'Testing...' : 'Test'}
              </button>
            )}
            <button
              onClick={handleEditToggle}
              disabled={saving}
              className="text-sm text-blue-600 hover:text-blue-800 font-medium disabled:opacity-50"
            >
              {isEditing ? 'Cancel' : 'Edit'}
            </button>
          </div>
        </div>
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          {/* Current Provider */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Provider</span>
            {isEditing ? (
              <select
                value={selectedProvider}
                onChange={(e) => setSelectedProvider(e.target.value)}
                className="text-sm border rounded px-2 py-1 bg-white min-w-[120px]"
              >
                {Object.keys(config.providers || {}).map(provider => (
                  <option key={provider} value={provider}>
                    {provider === 'azure' ? 'Azure OpenAI' : 'OpenAI'}
                  </option>
                ))}
              </select>
            ) : (
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${isAzure ? 'bg-blue-500' : 'bg-green-500'}`}></div>
                <span className="text-sm font-medium">
                  {isAzure ? 'Azure OpenAI' : 'OpenAI'}
                </span>
              </div>
            )}
          </div>

          {/* Current Model */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Model</span>
            {isEditing ? (
              <select
                value={selectedModel}
                onChange={(e) => setSelectedModel(e.target.value)}
                className="text-sm border rounded px-2 py-1 bg-white min-w-[160px] font-mono"
              >
                {config.providers[selectedProvider]?.chat_models?.map(model => (
                  <option key={model} value={model}>
                    {model}
                  </option>
                ))}
              </select>
            ) : (
              <span className="text-sm font-mono bg-white px-2 py-1 rounded border">
                {currentModel}
              </span>
            )}
          </div>

          {/* Temperature Control */}
          {isEditing && (
            <div className="flex items-center justify-between">
              <span className="text-sm text-gray-600">Temperature</span>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                defaultValue="0.7"
                className="w-24"
                title="Controls randomness (0 = deterministic, 2 = very creative)"
              />
            </div>
          )}

          {/* Azure-specific features */}
          {isAzure && !isEditing && (
            <>
              <div className="border-t border-gray-200 pt-3">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-600">API Type</span>
                  <span className="text-sm font-medium text-blue-600">
                    {azureFeatures.responses_api ? 'Responses API' : 'Chat Completions API'}
                  </span>
                </div>

                <div className="space-y-1">
                  <div className="text-xs text-gray-500 font-medium mb-1">Available Features:</div>
                  {Object.entries(azureFeatures).map(([feature, enabled]) => (
                    <div key={feature} className="flex items-center justify-between text-xs">
                      <span className="text-gray-600 capitalize">
                        {feature.replace(/_/g, ' ')}
                      </span>
                      <span className={`px-2 py-0.5 rounded text-xs font-medium ${
                        enabled
                          ? 'bg-green-100 text-green-800'
                          : 'bg-gray-100 text-gray-600'
                      }`}>
                        {enabled ? 'Enabled' : 'Disabled'}
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            </>
          )}

          {/* Available Models */}
          {!isEditing && (
            <div className="border-t border-gray-200 pt-3">
              <div className="text-xs text-gray-500 font-medium mb-2">
                Available Models ({config.providers[currentProvider]?.chat_models?.length || 0})
              </div>
              <div className="flex flex-wrap gap-1">
                {config.providers[currentProvider]?.chat_models?.slice(0, 6).map((model) => (
                  <span
                    key={model}
                    className={`text-xs px-2 py-1 rounded border ${
                      model === currentModel
                        ? 'bg-blue-100 text-blue-800 border-blue-200'
                        : 'bg-gray-100 text-gray-600 border-gray-200'
                    }`}
                  >
                    {model}
                  </span>
                ))}
                {config.providers[currentProvider]?.chat_models?.length > 6 && (
                  <span className="text-xs text-gray-500 px-2 py-1">
                    +{config.providers[currentProvider].chat_models.length - 6} more
                  </span>
                )}
              </div>
            </div>
          )}

          {/* Model Performance Indicators */}
          {!isEditing && (
            <div className="border-t border-gray-200 pt-3">
              <div className="text-xs text-gray-500 font-medium mb-2">Model Capabilities</div>
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Context Length</span>
                  <span className="font-mono">
                    {currentModel?.includes('gpt-4') ? '128k' : '4k'} tokens
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-gray-600">Code Generation</span>
                  <span className={`px-1 py-0.5 rounded text-xs ${
                    currentModel?.includes('gpt-4') || currentModel?.includes('claude')
                      ? 'bg-green-100 text-green-800'
                      : 'bg-yellow-100 text-yellow-800'
                  }`}>
                    {currentModel?.includes('gpt-4') || currentModel?.includes('claude') ? 'Excellent' : 'Good'}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Save Button */}
        {isEditing && (
          <div className="mt-4 flex justify-end space-x-2">
            <button
              onClick={() => setIsEditing(false)}
              disabled={saving}
              className="px-3 py-1 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={saving || validating || (selectedModel === currentModel && selectedProvider === currentProvider)}
              className="px-3 py-1 text-sm bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center"
            >
              {saving && (
                <svg className="animate-spin -ml-1 mr-2 h-3 w-3 text-white" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              )}
              {saving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default AIProviderInfo;