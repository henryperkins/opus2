// frontend/src/components/settings/AIProviderInfo.jsx
import { useConfig } from '../../hooks/useConfig';

const AIProviderInfo = () => {
  const { config, loading, error } = useConfig();

  if (loading) {
    return (
      <div className="animate-pulse">
        <div className="h-4 bg-gray-200 rounded w-1/4 mb-2"></div>
        <div className="h-3 bg-gray-200 rounded w-1/2"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-sm text-red-600">
        Failed to load AI provider configuration
      </div>
    );
  }

  if (!config) return null;

  const currentProvider = config.current?.provider;
  const currentModel = config.current?.chat_model;
  const isAzure = currentProvider === 'azure';
  const azureFeatures = isAzure ? config.providers?.azure?.features : {};

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-sm font-medium text-gray-900 mb-2">AI Provider</h3>
        <div className="bg-gray-50 rounded-lg p-4 space-y-3">
          {/* Current Provider */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Provider</span>
            <div className="flex items-center space-x-2">
              <div className={`w-2 h-2 rounded-full ${isAzure ? 'bg-blue-500' : 'bg-green-500'}`}></div>
              <span className="text-sm font-medium">
                {isAzure ? 'Azure OpenAI' : 'OpenAI'}
              </span>
            </div>
          </div>

          {/* Current Model */}
          <div className="flex items-center justify-between">
            <span className="text-sm text-gray-600">Model</span>
            <span className="text-sm font-mono bg-white px-2 py-1 rounded border">
              {currentModel}
            </span>
          </div>

          {/* Azure-specific features */}
          {isAzure && (
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
        </div>
      </div>
    </div>
  );
};

export default AIProviderInfo;
