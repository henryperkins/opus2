import React, { useState, useCallback, useEffect } from "react";
import {
  GitBranch,
  Globe,
  Lock,
  RefreshCw,
  CheckCircle,
  AlertCircle,
  Loader,
  ExternalLink,
} from "lucide-react";
import PropTypes from "prop-types";
import api from "../../api/client";
import { useWebSocketChannel } from "../../hooks/useWebSocketChannel";
import CredentialsModal from "./CredentialsModal";

const REPO_TYPES = {
  public: { icon: Globe, label: "Public Repository", color: "text-green-600" },
  private: {
    icon: Lock,
    label: "Private Repository",
    color: "text-yellow-600",
  },
};

export default function RepositoryConnect({
  projectId,
  onConnectSuccess,
  onError,
  disabled = false,
}) {
  const [formData, setFormData] = useState({
    repo_url: "",
    branch: "main",
    repo_type: "public",
    include_patterns: ["*.md", "*.txt", "*.rst", "README*", "docs/**/*"],
    exclude_patterns: ["node_modules/**/*", ".git/**/*", "*.log", "*.tmp"],
    token: "",
  });
  const [loading, setLoading] = useState(false);
  const [connected, setConnected] = useState(false);
  const [repoInfo, setRepoInfo] = useState(null);
  const [validationError, setValidationError] = useState("");
  const [progress, setProgress] = useState({ phase: "", percent: 0 });
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [currentJobId, setCurrentJobId] = useState(null);
  const [privateRepoToken, setPrivateRepoToken] = useState("");
  const [lastError, setLastError] = useState(null);
  const [retryCount, setRetryCount] = useState(0);

  const validateGitUrl = useCallback((url) => {
    const gitUrlPattern =
      /^(https?:\/\/|ssh:\/\/git@)[\w\.-]+[:\/][\w\.-]+\/[\w\.-]+\.git?$/i;
    const githubPattern = /^https:\/\/github\.com\/[\w\.-]+\/[\w\.-]+\/?$/i;

    if (!url) return "Repository URL is required";
    if (/\s/.test(url)) return "URL must not contain whitespace";
    if (!gitUrlPattern.test(url) && !githubPattern.test(url)) {
      return "Invalid Git repository URL format. Use HTTPS or git@github.com:user/repo.git format.";
    }
    return "";
  }, []);

  const handleChange = useCallback(
    (e) => {
      const { name, value } = e.target;
      setFormData((prev) => ({
        ...prev,
        [name]: value,
      }));

      if (name === "repo_url") {
        const error = validateGitUrl(value);
        setValidationError(error);
      }
    },
    [validateGitUrl],
  );

  const handlePatternChange = useCallback((e, type) => {
    const patterns = e.target.value.split("\n").filter((p) => p.trim());
    setFormData((prev) => ({
      ...prev,
      [`${type}_patterns`]: patterns,
    }));
  }, []);

  const fetchRepositoryInfo = useCallback(async () => {
    try {
      const response = await api.get(`/api/import/git/repository/${projectId}`);
      if (response.data.connected) {
        const repoData = response.data.repo_info;
        setRepoInfo({
          id: `project_${projectId}`,
          repo_name: repoData.repo_url.split("/").pop().replace(".git", ""),
          repo_url: repoData.repo_url,
          url: repoData.repo_url,
          branch: repoData.branch,
          commit_sha: repoData.commit_sha,
          total_files: response.data.stats.total_files,
          last_sync: repoData.last_sync,
          status: response.data.status,
        });
        setConnected(true);
        setFormData((prev) => ({
          ...prev,
          repo_url: repoData.repo_url,
          branch: repoData.branch,
        }));
        return response.data;
      }
    } catch (error) {
      console.error("Failed to fetch repository info:", error);
    }
    return null;
  }, [projectId]);

  const handleWebSocketMessage = useCallback(
    (event) => {
      if (event.type === "import" && event.job_id === currentJobId) {
        setProgress({ phase: event.phase, percent: event.percent });
        if (event.phase === "completed") {
          setLoading(false);
          fetchRepositoryInfo().then((data) => {
            if (data) {
              onConnectSuccess?.(data);
            }
          });
        } else if (event.phase === "failed") {
          setLoading(false);
          setCurrentJobId(null);
          setLastError(event.message || "Import failed");
          onError?.(event.message || "Import failed");
        }
      }
    },
    [currentJobId, onError, fetchRepositoryInfo, onConnectSuccess],
  );

  useWebSocketChannel("import", handleWebSocketMessage);

  // Check for existing repository connection on mount
  useEffect(() => {
    fetchRepositoryInfo();
  }, [fetchRepositoryInfo]);

  const connectRepository = useCallback(
    async (token = "") => {
      if (loading || validationError) return;

      setLoading(true);
      setProgress({ phase: "validating", percent: 0 });
      setLastError(null);

      try {
        const headers = token ? { "X-Git-Token": token } : {};

        // 1. Validate the repository
        const validationResponse = await api.post(
          "/api/import/git/validate",
          {
            repo_url: formData.repo_url,
            branch: formData.branch,
          },
          { headers },
        );

        setFormData((prev) => ({
          ...prev,
          branch: validationResponse.data.branch,
        }));

        // 2. Start the import job
        const importResponse = await api.post(
          "/api/import/git",
          {
            project_id: projectId,
            repo_url: formData.repo_url,
            branch: validationResponse.data.branch, // Use validated branch
            include_patterns: formData.include_patterns,
            exclude_patterns: formData.exclude_patterns,
          },
          { headers },
        );

        setCurrentJobId(importResponse.data.job_id);

        const newRepoInfo = {
          ...validationResponse.data,
          id: `job_${importResponse.data.job_id}`,
          status: "connecting",
          last_sync: new Date().toISOString(),
          repo_url: formData.repo_url,
          branch: validationResponse.data.branch,
        };
        setRepoInfo(newRepoInfo);
      } catch (error) {
        const errorMessage =
          error.response?.data?.detail ||
          error.message ||
          "An unknown error occurred.";
        console.error("Repository connection error:", errorMessage);
        onError?.(errorMessage);
        setValidationError(errorMessage);
        setLastError(errorMessage);
        setLoading(false);
        setRetryCount((prev) => prev + 1);
      }
    },
    [
      formData,
      loading,
      validationError,
      projectId,
      onConnectSuccess,
      onError,
      repoInfo,
    ],
  );

  const handleConnectClick = () => {
    if (formData.repo_type === "private") {
      setIsModalOpen(true);
    } else {
      connectRepository();
    }
  };

  const handleModalSubmit = (token) => {
    setFormData((prev) => ({ ...prev, token }));
    setPrivateRepoToken(token);
    connectRepository(token);
  };

  const retryLastOperation = useCallback(() => {
    if (formData.repo_type === "private" && privateRepoToken) {
      connectRepository(privateRepoToken);
    } else {
      connectRepository();
    }
  }, [formData.repo_type, privateRepoToken, connectRepository]);

  const disconnectRepository = useCallback(() => {
    setConnected(false);
    setRepoInfo(null);
    setProgress({ phase: "", percent: 0 });
    setFormData((prev) => ({ ...prev, repo_url: "", token: "" }));
    setPrivateRepoToken("");
    setCurrentJobId(null);
    setLastError(null);
    setRetryCount(0);
  }, []);

  const syncRepository = useCallback(async () => {
    if (!repoInfo || loading) return;

    setLoading(true);
    setProgress({ phase: "syncing", percent: 0 });

    try {
      const headers = privateRepoToken
        ? { "X-Git-Token": privateRepoToken }
        : {};

      // Start a new import job for the same repository
      const importResponse = await api.post(
        "/api/import/git",
        {
          project_id: projectId,
          repo_url: repoInfo.repo_url || formData.repo_url,
          branch: repoInfo.branch || formData.branch,
          include_patterns: formData.include_patterns,
          exclude_patterns: formData.exclude_patterns,
        },
        { headers },
      );

      setCurrentJobId(importResponse.data.job_id);

      // Update repo info with new job ID
      setRepoInfo((prev) => ({
        ...prev,
        id: `job_${importResponse.data.job_id}`,
        status: "syncing",
        last_sync: new Date().toISOString(),
      }));
    } catch (error) {
      const errorMessage =
        error.response?.data?.detail || error.message || "Sync failed";
      console.error("Repository sync error:", errorMessage);
      onError?.(errorMessage);
      setLoading(false);
    }
  }, [repoInfo, loading, projectId, formData, onError]);

  const RepoTypeIcon = REPO_TYPES[formData.repo_type]?.icon || Globe;

  if (connected && repoInfo) {
    return (
      <div className="space-y-4">
        {/* Connected Repository Info */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center space-x-2">
              <CheckCircle className="w-5 h-5 text-green-600" />
              <span className="text-sm font-medium text-green-800">
                Repository Connected
              </span>
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
                <strong>{repoInfo.repo_name}</strong> ({repoInfo.branch})
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
              <div>Files indexed: {repoInfo.total_files}</div>
              <div>
                Last sync: {new Date(repoInfo.last_sync).toLocaleString()}
              </div>
            </div>
          </div>
        </div>

        {/* Sync Options */}
        <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
          <span className="text-sm text-gray-700">
            Repository knowledge base
          </span>
          <button
            onClick={syncRepository}
            className="flex items-center space-x-1 px-3 py-1 text-xs bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50"
            disabled={disabled || loading}
          >
            <RefreshCw className="w-3 h-3" />
            <span>Sync Now</span>
          </button>
        </div>
      </div>
    );
  }

  if (loading) {
    return (
      <div className="p-4 border rounded-lg text-center">
        <Loader className="w-8 h-8 animate-spin mx-auto text-blue-600" />
        <p className="mt-2 text-sm font-medium text-gray-700 capitalize">
          {progress.phase}...
        </p>
        <div className="w-full bg-gray-200 rounded-full h-2.5 mt-2">
          <div
            className="bg-blue-600 h-2.5 rounded-full"
            style={{ width: `${progress.percent}%` }}
          ></div>
        </div>
        <p className="text-xs text-gray-500 mt-1">
          {progress.percent}% complete
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <CredentialsModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSubmit={handleModalSubmit}
      />

      {/* Error Display with Retry Option */}
      {lastError && !loading && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-4">
          <div className="flex items-start space-x-2">
            <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-sm text-red-800 font-medium">Import Failed</p>
              <p className="text-xs text-red-700 mt-1">{lastError}</p>
              {retryCount > 0 && (
                <p className="text-xs text-red-600 mt-1">
                  Retry attempt {retryCount}
                </p>
              )}
            </div>
            <button
              onClick={retryLastOperation}
              className="text-xs text-red-700 hover:text-red-900 underline"
            >
              Retry
            </button>
          </div>
        </div>
      )}

      {/* Repository URL Input */}
      <div>
        <label
          htmlFor="repo_url"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
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
              validationError ? "border-red-300 bg-red-50" : "border-gray-300"
            } ${disabled ? "bg-gray-50 text-gray-500" : ""}`}
          />
          <div className="absolute inset-y-0 right-0 flex items-center pr-3">
            <RepoTypeIcon
              className={`w-4 h-4 ${REPO_TYPES[formData.repo_type]?.color || "text-gray-400"}`}
            />
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
        <label
          htmlFor="branch"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
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
            disabled ? "bg-gray-50 text-gray-500" : ""
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
              <label
                key={type}
                className="flex items-center space-x-2 cursor-pointer"
              >
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
            value={formData.include_patterns.join("\n")}
            onChange={(e) => handlePatternChange(e, "include")}
            disabled={disabled || loading}
            rows={3}
            className={`w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              disabled ? "bg-gray-50 text-gray-500" : ""
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
            value={formData.exclude_patterns.join("\n")}
            onChange={(e) => handlePatternChange(e, "exclude")}
            disabled={disabled || loading}
            rows={3}
            className={`w-full px-3 py-2 border border-gray-300 rounded-lg text-xs focus:ring-2 focus:ring-blue-500 focus:border-blue-500 ${
              disabled ? "bg-gray-50 text-gray-500" : ""
            }`}
            placeholder="node_modules/**/*&#10;.git/**/*&#10;*.log"
          />
          <p className="mt-1 text-xs text-gray-500">One pattern per line</p>
        </div>
      </div>

      {/* Connect Button */}
      <button
        onClick={handleConnectClick}
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
  projectId: PropTypes.oneOfType([PropTypes.string, PropTypes.number])
    .isRequired,
  onConnectSuccess: PropTypes.func,
  onError: PropTypes.func,
  disabled: PropTypes.bool,
};
