// frontend/src/components/common/AIProviderStatus.jsx
import { useConfig } from '../../hooks/useConfig';
import PropTypes from 'prop-types';

const AIProviderStatus = ({ className = "" }) => {
  const { config, loading } = useConfig();

  if (loading || !config) {
    return null;
  }

  const currentProvider = config.current?.provider;
  const currentModel = config.current?.chat_model;

  const providerDisplayName = currentProvider === 'azure' ? 'Azure OpenAI' : 'OpenAI';
  const isAzure = currentProvider === 'azure';

  // Azure-specific features
  const azureFeatures = isAzure ? config.providers?.azure?.features : {};
  const hasResponsesAPI = azureFeatures?.responses_api;

  return (
    <div className={`flex items-center space-x-2 text-xs text-gray-600 ${className}`}>
      <div className="flex items-center space-x-1">
        <div className={`w-2 h-2 rounded-full ${isAzure ? 'bg-brand-primary-600' : 'bg-green-600'}`}></div>
        <span>{providerDisplayName}</span>
      </div>

      {currentModel && (
        <span className="text-gray-500">•</span>
      )}

      {currentModel && (
        <span className="font-mono">{currentModel}</span>
      )}

      {hasResponsesAPI && (
        <>
          <span className="text-gray-500">•</span>
          <span className="text-brand-primary-600 font-semibold">Responses API</span>
        </>
      )}
    </div>
  );
};

AIProviderStatus.propTypes = {
  className: PropTypes.string,
};

export default AIProviderStatus;
