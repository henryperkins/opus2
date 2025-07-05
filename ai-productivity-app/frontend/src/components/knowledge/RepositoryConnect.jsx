// Git repository connection interface for knowledge base integration
import React, { useState, useCallback } from 'react';
import { GitBranch, Globe, Lock, RefreshCw, CheckCircle, AlertCircle, Loader, ExternalLink } from 'lucide-react';
import PropTypes from 'prop-types';

const REPO_TYPES = {
  public: { icon: Globe, label: 'Public Repository', color: 'text-green-600' },
  private: { icon: Lock, label: 'Private Repository', color: 'text-yellow-600' }
};

export default function RepositoryConnect({ 
  projectId, 
  onConnectSuccess, 
  onError, 
  disabled = false 
}) {
  const [formData, setFormData] = useState({
    repo_url: '',
    branch: 'main',
    repo_type: 'public',
    include_patterns: ['*.md', '*.txt', '*.rst', 'README*', 'docs/**/*'],
    exclude_patterns: ['node_modules/**/*', '.git/**/*', '*.log', '*.tmp']
  });
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [repoInfo, setRepoInfo] = useState(null);
  const [validationError, setValidationError] = useState('');

  const validateGitUrl = useCallback((url) => {
    const gitUrlPattern = /^(https?:\/\/)?([\w\.-]+@)?[\w\.-]+[:\/][\w\.-]+\/[\w\.-]+\.git?$/;
    const githubPattern = /^https:\/\/github\.com\/[\w\.-]+\/[\w\.-]+\/?$/;
    
    if (!url) return 'Repository URL is required';
    if (!gitUrlPattern.test(url) && !githubPattern.test(url)) {
      return 'Invalid Git repository URL format';
    }
    return '';
  }, []);

  const handleChange = useCallback((e) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));

    if (name === 'repo_url') {
      const error = validateGitUrl(value);
      setValidationError(error);
    }
  }, [validateGitUrl]);

  const handlePatternChange = useCallback((e, type) => {
    const patterns = e.target.value.split('\n').filter(p => p.trim());
    setFormData(prev => ({
      ...prev,
      [`${type}_patterns`]: patterns
    }));
  }, []);

  const parseRepoUrl = useCallback((url) => {
    try {
      if (url.includes('github.com')) {
        const match = url.match(/github\.com[\/:]([^\/]+)\/([^\/\.]+)/);
        if (match) {
          return {
            platform: 'GitHub',
            owner: match[1],
            name: match[2],
            url: `https://github.com/${match[1]}/${match[2]}`
          };
        }
      }
      
      // Generic Git URL parsing
      const match = url.match(/([^\/]+)\/([^\/\.]+)\.git?$/);
      if (match) {
        return {
          platform: 'Git',
          owner: match[1],
          name: match[2],
          url: url
        };
      }
    } catch (error) {
      console.error('Error parsing repo URL:', error);
    }
    return null;
  }, []);

  const connectRepository = useCallback(async () => {
    if (loading || validationError) return;

    setLoading(true);

    try {
      // Parse repository information
      const repoData = parseRepoUrl(formData.repo_url);
      if (!repoData) {
        throw new Error('Unable to parse repository URL');
      }

      // Mock repository connection - in production, this would integrate with code ingestion API
      const mockResponse = await new Promise((resolve) => {
        setTimeout(() => {
          resolve({
            success: true,
            data: {
              id: `repo_${Date.now()}`,
              ...repoData,
              branch: formData.branch,
              status: 'connected',
              last_sync: new Date().toISOString(),
              files_indexed: Math.floor(Math.random() * 500) + 50,
              documents_added: Math.floor(Math.random() * 100) + 10
            }
          });
        }, 2000);
      });

      if (mockResponse.success) {
        setRepoInfo(mockResponse.data);
        setConnected(true);
        onConnectSuccess?.(mockResponse.data);
      } else {
        throw new Error(mockResponse.message || 'Failed to connect repository');
      }
    } catch (error) {
      console.error('Repository connection error:', error);
      onError?.(error.message);
    } finally {
      setLoading(false);
    }
  }, [formData, loading, validationError, parseRepoUrl, onConnectSuccess, onError]);

  const disconnectRepository = useCallback(() => {
    setConnected(false);
    setRepoInfo(null);
    setFormData(prev => ({ ...prev, repo_url: '' }));
  }, []);

  const RepoTypeIcon = REPO_TYPES[formData.repo_type]?.icon || Globe;

  if (connected && repoInfo) {
    return (
      <div className="space-y-4">
        {/* Connected Repository Info */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="text-sm font-medium text-green-800">Repository Connected</span>
            </div>
            <button
              onClick={disconnectRepository}
              className="text-xs text-green-700 hover:text-green-900 underline"
            >
              Disconnect
            </button>
          </div>

          <div className="space-y-2">
            <div className="flex items-center space-x-2">
              <GitBranch className="w-4 h-4 text-gray-500" />
              <span className="text-sm text-gray-700">
                <strong>{repoInfo.owner}/{repoInfo.name}</strong> ({repoInfo.branch})
              </span>
              <a
                href={repoInfo.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-blue-600 hover:text-blue-800"
              >
                <ExternalLink className="w-3 h-3" />
              </a>
            </div>

            <div className="text-xs text-gray-600 space-y-1">
              <div>Files indexed: {repoInfo.files_indexed}</div>
              <div>Documents added: {repoInfo.documents_added}</div>
              <div>Last sync: {new Date(repoInfo.last_sync).toLocaleString()}</div>
            </div>
          </div>
        </div>

        {/* Sync Options */}
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span className="text-sm text-gray-700">Repository knowledge base</span>
          <button
            className="flex items-center space-x-1 px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700"
            disabled={disabled}
          >
            <RefreshCw className="w-3 h-3" />
            <span>Sync Now</span>
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Repository URL Input */}
      <div>
        <label htmlFor="repo_url" className="block text-sm font-medium text-gray-700 mb-1">
          Repository URL
        </label>
        <div className="relative">
          <input
            type="url"
            id="repo_url"
            name="repo_url"
            value={formData.repo_url}
            onChange={handleChange}
            placeholder="https://github.com/user/repository.git"
            disabled={disabled || loading}
            className={`w-full px-3 py-2 border rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              validationError 
                ? 'border-red-300 bg-red-50' 
                : 'border-gray-300'
            } ${disabled ? 'bg-gray-50 text-gray-500' : ''}`}
          />
          <div className="absolute inset-y-0 right-0 flex items-center pr-3">
            <RepoTypeIcon className={`w-4 h-4 ${REPO_TYPES[formData.repo_type]?.color || 'text-gray-400'}`} />
          </div>
        </div>
        {validationError && (
          <p className="mt-1 text-xs text-red-600 flex items-center space-x-1">
            <AlertCircle className="w-3 h-3" />
            <span>{validationError}</span>
          </p>
        )}
        <p className="mt-1 text-xs text-gray-500">
          Supports GitHub, GitLab, Bitbucket, and other Git repositories
        </p>
      </div>

      {/* Branch Selection */}
      <div>
        <label htmlFor="branch" className="block text-sm font-medium text-gray-700 mb-1">
          Branch
        </label>
        <input
          type="text"
          id="branch"
          name="branch"
          value={formData.branch}
          onChange={handleChange}
          placeholder="main"
          disabled={disabled || loading}
          className={`w-full px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
            disabled ? 'bg-gray-50 text-gray-500' : ''
          }`}
        />
      </div>

      {/* Repository Type */}
      <div>
        <label className="block text-sm font-medium text-gray-700 mb-2">
          Repository Type
        </label>
        <div className="flex space-x-4">
          {Object.entries(REPO_TYPES).map(([type, config]) => {
            const Icon = config.icon;
            return (
              <label key={type} className="flex items-center space-x-2 cursor-pointer">
                <input
                  type="radio"
                  name="repo_type"
                  value={type}
                  checked={formData.repo_type === type}
                  onChange={handleChange}
                  disabled={disabled || loading}
                  className="text-blue-600 focus:ring-blue-500"
                />
                <Icon className={`w-4 h-4 ${config.color}`} />
                <span className="text-sm text-gray-700">{config.label}</span>
              </label>
            );
          })}
        </div>
      </div>

      {/* File Patterns */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Include Patterns
          </label>
          <textarea
            value={formData.include_patterns.join('\n')}
            onChange={(e) => handlePatternChange(e, 'include')}
            disabled={disabled || loading}
            rows={3}
            className={`w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              disabled ? 'bg-gray-50 text-gray-500' : ''
            }`}
            placeholder="*.md&#10;*.txt&#10;README*"
          />
          <p className="mt-1 text-xs text-gray-500">One pattern per line</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700 mb-1">
            Exclude Patterns
          </label>
          <textarea
            value={formData.exclude_patterns.join('\n')}
            onChange={(e) => handlePatternChange(e, 'exclude')}
            disabled={disabled || loading}
            rows={3}
            className={`w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              disabled ? 'bg-gray-50 text-gray-500' : ''
            }`}
            placeholder="node_modules/**/*&#10;.git/**/*&#10;*.log"
          />
          <p className="mt-1 text-xs text-gray-500">One pattern per line</p>
        </div>
      </div>

      {/* Connect Button */}
      <button
        onClick={connectRepository}
        disabled={disabled || loading || !formData.repo_url || validationError}
        className="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2 text-sm font-medium"
      >
        {loading ? (
          <>
            <Loader className="w-4 h-4 animate-spin" />
            <span>Connecting Repository...</span>
          </>
        ) : (
          <>
            <GitBranch className="w-4 h-4" />
            <span>Connect Repository</span>
          </>
        )}
      </button>

      <div className="text-xs text-gray-500 space-y-1">
        <p>• Repository files will be indexed for knowledge search</p>
        <p>• Only text-based documents will be processed</p>
        <p>• Large repositories may take several minutes to index</p>
      </div>
    </div>
  );
}

RepositoryConnect.propTypes = {
  projectId: PropTypes.oneOfType([PropTypes.string, PropTypes.number]).isRequired,
  onConnectSuccess: PropTypes.func,
  onError: PropTypes.func,
  disabled: PropTypes.bool,
};