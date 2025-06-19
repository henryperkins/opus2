// frontend/src/pages/ProjectChatPage.jsx
/* global navigator */
import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useChat } from '../hooks/useChat';
import { useProject, useProjectTimeline } from '../hooks/useProjects';
import Header from '../components/common/Header';
import MessageList from '../components/chat/MessageList';
import CommandInput from '../components/chat/CommandInput';
import CodePreview from '../components/chat/CodePreview';
import MonacoEditor from '@monaco-editor/react';
import { codeAPI } from '../api/code';
import chatAPI from '../api/chat';
import FileUpload from '../components/knowledge/FileUpload';
import DependencyGraph from '../components/knowledge/DependencyGraph';
import SplitPane from '../components/common/SplitPane';
import { createTwoFilesPatch } from 'diff';

// Tracks projects with files already fetched
const filesFetchedForProject = new Set();

export default function ProjectChatPage() {
  const { projectId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  // Prefer project passed via navigation state to avoid an extra API call.
  const stateProject = location.state?.project;

  const { project: fetchedProject, loading: projectLoading, fetch: fetchProject } = useProject(projectId);
  const { addEvent } = useProjectTimeline(projectId);

  const project = stateProject || fetchedProject;
  const [sessionId, setSessionId] = useState(null);
  const [editorContent, setEditorContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [editorLanguage, setEditorLanguage] = useState('python');
  const [showDiff, setShowDiff] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [projectFiles, setProjectFiles] = useState([]);
  const [splitView, setSplitView] = useState(true);
  const [rightPanelMode, setRightPanelMode] = useState('editor');

  const refreshFiles = () => {
    fetchProjectFiles();
  };

  // Create or get chat session
  useEffect(() => {
    if (!project && projectId && !stateProject) {
      // Fetch project details only if not provided via state
      fetchProject();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, stateProject]);

  useEffect(() => {
    if (!projectId) return;

    // Create chat session once per mount
    if (!sessionId) {
      chatAPI
        .createSession(projectId)
        .then((resp) => {
          setSessionId(resp.id);
        })
        .catch((err) => {
          console.error('Failed to create chat session:', err);
        });
    }

    if (!filesFetchedForProject.has(projectId)) {
      fetchProjectFiles().finally(() => filesFetchedForProject.add(projectId));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, sessionId]);

  const fetchProjectFiles = async () => {
    try {
      const response = await codeAPI.getProjectFiles(projectId);
      setProjectFiles(response.files || []);
    } catch (err) {
      if (err.response?.status === 404) {
        setProjectFiles([]);
      } else {
        console.error('Failed to fetch project files:', err);
      }
    }
  };

  const handleDeleteFile = async (id) => {
    if (!window.confirm('Delete this file?')) return;
    try {
      await codeAPI.deleteFile(id);
      refreshFiles();
    } catch (err) {
      console.error('Failed to delete file:', err);
    }
  };

  const {
    messages,
    connectionState,
    typingUsers,
    sendMessage,
    editMessage,
    deleteMessage,
    sendTypingIndicator
  } = useChat(sessionId);

  const handleSendMessage = (content, metadata) => {
    // Include current editor content if mentioned
    if (content.includes('@code') || content.includes('@editor')) {
      metadata.code_snippets = [{
        language: editorLanguage,
        code: editorContent,
        file_path: selectedFile?.path || 'untitled'
      }];
    }

    sendMessage(content, metadata);
  };

  const handleCodeSelect = (codeBlock) => {
    setEditorContent(codeBlock.code);
    setEditorLanguage(codeBlock.language);
  };

  const handleFileSelect = async (file) => {
    setSelectedFile(file);
    try {
      const content = await codeAPI.getFileContent(file.id);
      setEditorContent(content.content);
      setOriginalContent(content.content);
      setEditorLanguage(file.language);
    } catch (err) {
      console.error('Failed to load file:', err);
    }
  };

  const handleSaveDiff = async () => {
    if (!selectedFile) return;
    const patch = createTwoFilesPatch(
      selectedFile.path,
      selectedFile.path,
      originalContent,
      editorContent,
      '',
      ''
    );
    try {
      await addEvent({
        event_type: 'updated',
        title: `Edited ${selectedFile.path}`,
        description: 'Code updated via editor',
        metadata: { file_path: selectedFile.path, diff: patch }
      });
      setOriginalContent(editorContent);
    } catch (err) {
      console.error('Failed to save diff:', err);
    }
  };

  if (projectLoading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
      </div>
    );
  }

  if (!project) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-gray-900">Project not found</h2>
          <button
            onClick={() => navigate('/projects')}
            className="mt-4 text-blue-600 hover:text-blue-800"
          >
            Back to Projects
          </button>
        </div>
      </div>
    );
  }

  const chatPanel = (
    <div className="flex flex-col h-full bg-white border-r border-gray-200">
      <div className="p-4 border-b flex items-center justify-between">
        <h2 className="text-lg font-semibold text-gray-900">AI Chat</h2>
        <button
          onClick={() => setSplitView(!splitView)}
          className="text-gray-600 hover:text-gray-900"
          title={splitView ? 'Hide editor' : 'Show editor'}
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {splitView ? (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M11 19l-7-7 7-7m8 14l-7-7 7-7" />
            ) : (
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
            )}
          </svg>
        </button>
      </div>

      <div className="flex-1 overflow-hidden">
        <MessageList
          messages={messages}
          onCodeSelect={handleCodeSelect}
          onMessageEdit={editMessage}
          onMessageDelete={deleteMessage}
          currentUserId={1} // Replace with actual user ID
        />
      </div>

      {typingUsers.size > 0 && (
        <div className="px-4 py-2 text-sm text-gray-500">
          {typingUsers.size} user{typingUsers.size > 1 ? 's' : ''} typing...
        </div>
      )}

      {connectionState !== 'connected' && (
        <div className="px-4 py-2 bg-yellow-50 text-yellow-800 text-sm">
          {connectionState === 'connecting' ? 'Connecting...' : 'Disconnected'}
        </div>
      )}

      <CommandInput
        onSend={handleSendMessage}
        onTyping={sendTypingIndicator}
        projectId={projectId}
      />
    </div>
  );

  const editorPanel = (
    <div className="flex flex-col h-full bg-white">
      <div className="p-4 border-b flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <span className="text-sm font-medium text-gray-700">
            {selectedFile ? selectedFile.path : 'Untitled'}
          </span>
          <select
            value={editorLanguage}
            onChange={(e) => setEditorLanguage(e.target.value)}
            className="text-sm border rounded px-2 py-1"
          >
            <option value="python">Python</option>
            <option value="javascript">JavaScript</option>
            <option value="typescript">TypeScript</option>
          </select>
        </div>

        <div className="flex items-center space-x-2">
          <button
            onClick={() => setShowDiff(!showDiff)}
            className={`text-sm px-3 py-1 rounded ${
              showDiff ? 'bg-blue-500 text-white' : 'bg-gray-100'
            }`}
          >
            Diff
          </button>
          <button
            onClick={handleSaveDiff}
            className="text-sm px-3 py-1 rounded bg-green-500 text-white"
          >
            Save Diff
          </button>
          <button
            onClick={() =>
              setRightPanelMode(rightPanelMode === 'canvas' ? 'editor' : 'canvas')
            }
            className={`text-sm px-3 py-1 rounded ${
              rightPanelMode === 'canvas' ? 'bg-blue-500 text-white' : 'bg-gray-100'
            }`}
          >
            {rightPanelMode === 'canvas' ? 'Editor' : 'Canvas'}
          </button>
          <button
            onClick={() => {
              navigator.clipboard.writeText(editorContent).catch(() => {
                alert('Failed to copy code to clipboard.');
              });
            }}
            className="p-1 text-gray-600 hover:text-gray-900"
            title="Copy code"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
            </svg>
          </button>
        </div>
      </div>

      <div className="flex-1">
        <MonacoEditor
          value={editorContent}
          language={editorLanguage}
          onChange={setEditorContent}
          theme="vs-dark"
          options={{
            minimap: { enabled: false },
            fontSize: 14,
            wordWrap: 'on',
            automaticLayout: true
          }}
        />
      </div>
    </div>
  );

  const canvasPanel = (
    <div className="flex flex-col h-full bg-white">
      <div className="p-4 border-b flex items-center justify-between">
        <h3 className="text-lg font-medium text-gray-900">Canvas</h3>
        <button
          onClick={() => setRightPanelMode('editor')}
          className="text-sm text-gray-600 hover:text-gray-900"
        >
          Close
        </button>
      </div>
      <div className="flex-1 overflow-auto p-4">
        <DependencyGraph projectId={projectId} />
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col">
      <Header />

      <div className="flex-1 flex overflow-hidden">
        {/* File Explorer Sidebar */}
        <div className="w-64 bg-white border-r border-gray-200 flex flex-col">
          <div className="p-4 border-b">
            <h3 className="font-semibold text-gray-900 flex items-center">
              <span className="text-xl mr-2">{project.emoji}</span>
              {project.title}
            </h3>
          </div>

          <div className="flex-1 overflow-y-auto p-4">
            <h4 className="text-sm font-medium text-gray-700 mb-2">Files</h4>
            {projectFiles.length > 0 ? (
              <ul className="space-y-1">
                {projectFiles.map(file => (
                  <li key={file.id} className="flex items-center justify-between group">
                    <button
                      onClick={() => handleFileSelect(file)}
                      className={`flex-1 text-left px-2 py-1 rounded text-sm truncate hover:bg-gray-100 ${
                        selectedFile?.id === file.id ? 'bg-blue-50 text-blue-700' : ''
                      }`}
                    >
                      {file.path.split('/').pop()}
                    </button>
                    <button
                      onClick={() => handleDeleteFile(file.id)}
                      className="opacity-0 group-hover:opacity-100 p-1 text-red-500 hover:text-red-700"
                      title="Delete file"
                    >
                      <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M6 18L18 6M6 6l12 12" />
                      </svg>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="text-sm text-gray-500">No files uploaded yet</p>
            )}
          </div>
          {/* Upload section */}
          <div className="p-4 border-t">
            <FileUpload projectId={projectId} onSuccess={refreshFiles} />
          </div>
        </div>

        {/* Main Content Area */}
        <div className="flex-1">
          {splitView ? (
            <SplitPane
              left={chatPanel}
              right={rightPanelMode === 'canvas' ? canvasPanel : editorPanel}
            />
          ) : (
            chatPanel
          )}
        </div>
      </div>
    </div>
  );
}
