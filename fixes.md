// ============================================
  // FIX 1: Update ProjectChatPage to Remove ChatHeader
  // ============================================
  // File: src/pages/ProjectChatPage.jsx

  // REMOVE this import (line 19):
  // import ChatHeader from '../components/chat/ChatHeader';

  // REMOVE the ChatHeader component usage (around line 592) and move its
   functionality to context actions:
  // Delete this entire block:
  /*
  <ChatHeader
    project={project}
    connectionState={connectionState}
    messages={messages}
    showKnowledgeAssistant={showKnowledgeAssistant}
    showEditor={showMonacoEditor}
    onToggleKnowledge={() => 
  setShowKnowledgeAssistant(!showKnowledgeAssistant)}
    onToggleEditor={() => setShowMonacoEditor(!showMonacoEditor)}
    onOpenSearch={() => setShowSearch(true)}
    onOpenPromptManager={() => setShowPromptManager(true)}
    onToggleAnalytics={() => setShowAnalytics(v => !v)}
  />
  */

  // ADD connection indicator inside the chat area instead:
  export default function ProjectChatPage() {
    // ... existing code ...

    // Add handler for context actions from UnifiedNavBar
    useEffect(() => {
      const handleContextAction = (event) => {
        switch (event.detail) {
          case 'knowledge':
            setShowKnowledgeAssistant(!showKnowledgeAssistant);
            break;
          case 'editor':
            setShowMonacoEditor(!showMonacoEditor);
            break;
          case 'search':
            setShowSearch(true);
            break;
          case 'settings':
            setShowPromptManager(true);
            break;
          case 'analytics':
            setShowAnalytics(v => !v);
            break;
        }
      };

      window.addEventListener('contextAction', handleContextAction);
      return () => window.removeEventListener('contextAction', 
  handleContextAction);
    }, [showKnowledgeAssistant, showMonacoEditor]);

    return (
      <div className="flex flex-col h-full bg-gray-50 dark:bg-gray-900 
  overflow-hidden">
        {/* Main Layout - NO HEADER HERE */}
        <ChatLayout
          showSidebar={showKnowledgeAssistant}
          showEditor={showMonacoEditor}
          // ... rest of props
        >
          {/* Chat Interface */}
          <div className="flex flex-col h-full">
            {/* Connection Status Bar */}
            <div className="px-4 py-2 border-b border-gray-200 
  dark:border-gray-700 flex items-center justify-between">
              <ConnectionIndicator state={connectionState} />
              <SessionRAGBadge messages={messages} />
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4" 
  ref={messageListRef}>
              {/* ... message list content ... */}
            </div>

            {/* Input */}
            <div className="sticky bottom-0 bg-white dark:bg-gray-900 
  border-t border-gray-200 dark:border-gray-700 p-4">
              <EnhancedCommandInput
                // ... props
              />
            </div>
          </div>
        </ChatLayout>
      </div>
    );
  }

  // ============================================
  // FIX 2: Update AppShell to Dispatch Context Actions
  // ============================================
  // File: src/components/common/AppShell.jsx

  // UPDATE the handleContextAction function:
  const handleContextAction = (actionId) => {
    // Dispatch custom event that pages can listen to
    window.dispatchEvent(new CustomEvent('contextAction', { detail: 
  actionId }));
    
    // Handle global actions
    switch (actionId) {
      case 'settings':
        // Could navigate to settings or open a modal
        break;
      case 'analytics':
        // Could toggle global analytics view
        break;
    }
  };

  // ============================================
  // FIX 3: Update UnifiedSettingsPage to Use NavigationManager
  // ============================================
  // File: src/pages/UnifiedSettingsPage.jsx

  // ADD import at top:
  import { NavigationManager } from '../utils/navigation';

  // REPLACE the hardcoded styles in the settings navigation:
  export default function UnifiedSettingsPage() {
    const { user } = useAuth();
    const [activeSection, setActiveSection] = useState('profile');

    return (
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex gap-8">
          {/* Settings Navigation */}
          <nav className="w-64 flex-shrink-0">
            <ul className="space-y-1">
              {SETTINGS_SECTIONS.map(section => {
                const Icon = section.icon;
                const isActive = activeSection === section.id;
                return (
                  <li key={section.id}>
                    <button
                      onClick={() => setActiveSection(section.id)}
                      className={`w-full flex items-center space-x-3 px-3
   py-2 rounded-lg text-sm font-medium transition-colors ${
                        NavigationManager.getActiveStyles(isActive, 
  'sidebar')
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span>{section.label}</span>
                    </button>
                  </li>
                );
              })}
            </ul>
          </nav>
          {/* ... rest of component */}
        </div>
      </div>
    );
  }

  // ============================================
  // FIX 4: Update UnifiedSidebar to Use NavigationManager
  // ============================================
  // File: src/components/navigation/UnifiedSidebar.jsx

  // The component should already import NavigationManager through 
  useNavigation context
  // But for any hardcoded styles, replace them:

  // REPLACE any instance of:
  className={`block px-3 py-2 text-sm rounded-lg truncate 
  transition-colors ${
    isActive
      ? 'bg-blue-50 dark:bg-blue-900/20 text-blue-700 dark:text-blue-300'
      : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 
  dark:hover:bg-gray-800'
  }`}

  // WITH:
  className={`block px-3 py-2 text-sm rounded-lg truncate 
  transition-colors ${
    getActiveStyles(path, 'sidebar')
  }`}

  // ============================================
  // FIX 5: Remove Old Components
  // ============================================

  # Run these commands to remove old components:
  rm src/components/common/Sidebar.jsx
  rm src/components/common/Breadcrumb.jsx
  rm src/components/projects/ProjectHeader.jsx

  # Or mark them as deprecated if you need a gradual migration:
  // Add to top of old files:
  console.warn('DEPRECATED: This component is deprecated. Use Unified 
  components instead.');

  // ============================================
  // FIX 6: Update Any Remaining Imports
  // ============================================

  # Find and replace old imports:
  # Search for:
  import Sidebar from '../common/Sidebar'
  import Breadcrumb from '../common/Breadcrumb'
  import ChatHeader from '../chat/ChatHeader'

  # Replace with appropriate unified components or remove if not needed
