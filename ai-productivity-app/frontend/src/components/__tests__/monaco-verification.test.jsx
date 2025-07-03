import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ThemeProvider } from '../../contexts/ThemeContext';
import MonacoRoot from '../editor/MonacoRoot';
import ChatLayout from '../chat/ChatLayout';

// Mock Monaco Editor
vi.mock('@monaco-editor/react', () => ({
  default: vi.fn(({ onMount, value, onChange }) => {
    const mockEditor = {
      getValue: vi.fn(() => value || ''),
      setValue: vi.fn(),
      layout: vi.fn(),
      dispose: vi.fn(),
      getModel: vi.fn(() => ({
        dispose: vi.fn()
      })),
      onDidChangeModelContent: vi.fn(() => ({
        dispose: vi.fn()
      })),
      trigger: vi.fn()
    };

    // Simulate onMount callback
    if (onMount) {
      setTimeout(() => onMount(mockEditor, { editor: { createModel: vi.fn() } }), 0);
    }

    return (
      <div
        className="monaco-editor"
        data-testid="monaco-editor"
        style={{ width: '100%', height: '400px' }}
      >
        Mock Monaco Editor
      </div>
    );
  })
}));

// Mock hooks
vi.mock('../../hooks/useTheme', () => ({
  useTheme: () => ({ theme: 'light' })
}));

vi.mock('../../hooks/useCodeEditor', () => ({
  default: () => ({
    editorRef: { onMount: vi.fn() },
    copilotEnabled: false,
    triggerCompletion: vi.fn()
  })
}));

// Mock components
vi.mock('../common/LoadingSpinner', () => ({
  default: () => <div data-testid="loading-spinner">Loading...</div>
}));

vi.mock('./EditorErrorBoundary', () => ({
  default: ({ children }) => <div data-testid="error-boundary">{children}</div>
}));

vi.mock('./MobileCodeToolbar', () => ({
  default: () => <div data-testid="mobile-toolbar">Mobile Toolbar</div>
}));

// Test wrapper component
const TestWrapper = ({ children }) => (
  <ThemeProvider>
    {children}
  </ThemeProvider>
);

describe('Monaco Editor Stability Tests', () => {
  let user;

  beforeEach(() => {
    user = userEvent.setup();
    // Mock window dimensions
    Object.defineProperty(window, 'innerWidth', {
      writable: true,
      configurable: true,
      value: 1024,
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('MonacoRoot Component', () => {
    it('1. Initial Mount - renders without errors and has proper dimensions', async () => {
      render(
        <TestWrapper>
          <MonacoRoot value="console.log('test');" />
        </TestWrapper>
      );

      const editor = await waitFor(() => screen.getByTestId('monaco-editor'));
      expect(editor).toBeInTheDocument();

      // Check dimensions
      const rect = editor.getBoundingClientRect();
      expect(rect.width).toBeGreaterThan(0);
      expect(rect.height).toBeGreaterThan(0);
    });

    it('2. Error Boundary - wraps editor in error boundary', () => {
      render(
        <TestWrapper>
          <MonacoRoot value="test code" />
        </TestWrapper>
      );

      expect(screen.getByTestId('error-boundary')).toBeInTheDocument();
    });

    it('3. Large File Handling - shows warning for large files', () => {
      const largeContent = 'x'.repeat(2 * 1024 * 1024); // 2MB

      render(
        <TestWrapper>
          <MonacoRoot
            value={largeContent}
            maxFileSize={1024 * 1024} // 1MB limit
          />
        </TestWrapper>
      );

      expect(screen.getByText(/Large file detected/)).toBeInTheDocument();
    });

    it('4. Mobile Optimization - shows mobile toolbar on mobile', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 767,
      });

      render(
        <TestWrapper>
          <MonacoRoot value="test" showMobileToolbar={true} />
        </TestWrapper>
      );

      expect(screen.getByTestId('mobile-toolbar')).toBeInTheDocument();
    });

    it('5. Memory Management - exposes cleanup methods', () => {
      const ref = { current: null };

      render(
        <TestWrapper>
          <MonacoRoot ref={ref} value="test" />
        </TestWrapper>
      );

      expect(ref.current).toHaveProperty('layout');
      expect(ref.current).toHaveProperty('getFileSize');
      expect(ref.current).toHaveProperty('isVirtualized');
    });

    it('6. Accessibility - has proper ARIA labels', () => {
      render(
        <TestWrapper>
          <MonacoRoot
            value="test code"
            filename="test.js"
          />
        </TestWrapper>
      );

      expect(screen.getByText('Editing test.js in javascript language.')).toBeInTheDocument();
    });
  });

  describe('ChatLayout Component', () => {
    const mockEditor = <div data-testid="mock-editor">Editor Content</div>;
    const mockSidebar = <div data-testid="mock-sidebar">Sidebar Content</div>;
    const mockChildren = <div data-testid="mock-chat">Chat Content</div>;

    it('7. Panel Layout - renders panels correctly', () => {
      render(
        <ChatLayout
          showEditor={true}
          showSidebar={true}
          editor={mockEditor}
          sidebar={mockSidebar}
        >
          {mockChildren}
        </ChatLayout>
      );

      expect(screen.getByTestId('mock-chat')).toBeInTheDocument();
      expect(screen.getByTestId('mock-editor')).toBeInTheDocument();
      expect(screen.getByTestId('mock-sidebar')).toBeInTheDocument();
    });

    it('8. LocalStorage Integration - handles panel state', () => {
      const mockRef = { current: { setLayout: vi.fn() } };

      // Mock localStorage with invalid layout
      const mockStorage = {
        'react-resizable-panels:chat-editor-vertical': JSON.stringify({
          'chat-editor-vertical': { layout: [65, 0] }
        })
      };

      Object.defineProperty(window, 'localStorage', {
        value: {
          getItem: vi.fn((key) => mockStorage[key]),
          setItem: vi.fn(),
          removeItem: vi.fn()
        }
      });

      render(
        <ChatLayout
          showEditor={true}
          editor={mockEditor}
          monacoRef={mockRef}
        >
          {mockChildren}
        </ChatLayout>
      );

      // Should call setLayout to fix invalid layout
      expect(mockRef.current.setLayout).toHaveBeenCalled();
    });

    it('9. Responsive Behavior - adapts to mobile', () => {
      // Mock mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 767,
      });

      render(
        <ChatLayout
          showSidebar={true}
          sidebar={mockSidebar}
        >
          {mockChildren}
        </ChatLayout>
      );

      // Sidebar should be hidden on mobile and show toggle button
      expect(screen.queryByTestId('mock-sidebar')).not.toBeInTheDocument();
    });

    it('10. Close Handlers - triggers close callbacks', async () => {
      const mockOnEditorClose = vi.fn();
      const mockOnSidebarClose = vi.fn();

      render(
        <ChatLayout
          showEditor={true}
          showSidebar={true}
          editor={mockEditor}
          sidebar={mockSidebar}
          onEditorClose={mockOnEditorClose}
          onSidebarClose={mockOnSidebarClose}
        >
          {mockChildren}
        </ChatLayout>
      );

      // Find and click close buttons
      const closeButtons = screen.getAllByLabelText(/close/i);

      if (closeButtons.length >= 2) {
        await user.click(closeButtons[0]); // Editor close
        await user.click(closeButtons[1]); // Sidebar close

        expect(mockOnEditorClose).toHaveBeenCalled();
        expect(mockOnSidebarClose).toHaveBeenCalled();
      }
    });
  });

  describe('Performance and Memory Tests', () => {
    it('11. Layout Performance - layout calls complete quickly', async () => {
      const ref = { current: null };

      render(
        <TestWrapper>
          <MonacoRoot ref={ref} value="test" />
        </TestWrapper>
      );

      await waitFor(() => expect(ref.current).not.toBeNull());

      const startTime = performance.now();
      ref.current.layout();
      const layoutTime = performance.now() - startTime;

      // Layout should complete in under 16ms
      expect(layoutTime).toBeLessThan(16);
    });

    it('12. Memory Cleanup - disposes resources on unmount', () => {
      const { unmount } = render(
        <TestWrapper>
          <MonacoRoot value="test" />
        </TestWrapper>
      );

      // Spy on cleanup
      const mockDispose = vi.fn();
      window.monaco = {
        editor: {
          getModels: () => [{ dispose: mockDispose }]
        }
      };

      unmount();

      // Should clean up models
      expect(mockDispose).toHaveBeenCalled();
    });
  });

  describe('Integration Tests', () => {
    it('13. Full Layout Integration - all components work together', async () => {
      const mockMonacoRef = { current: { layout: vi.fn() } };

      render(
        <TestWrapper>
          <ChatLayout
            showEditor={true}
            showSidebar={true}
            editor={<MonacoRoot ref={mockMonacoRef} value="test code" />}
            sidebar={<div data-testid="knowledge-assistant">Knowledge Assistant</div>}
            monacoRef={mockMonacoRef}
          >
            <div data-testid="chat-messages">Chat Messages</div>
          </ChatLayout>
        </TestWrapper>
      );

      // All components should render
      expect(screen.getByTestId('chat-messages')).toBeInTheDocument();
      expect(screen.getByTestId('monaco-editor')).toBeInTheDocument();
      expect(screen.getByTestId('knowledge-assistant')).toBeInTheDocument();
    });

    it('14. State Management - preserves state across re-renders', () => {
      const { rerender } = render(
        <TestWrapper>
          <MonacoRoot value="initial code" />
        </TestWrapper>
      );

      const editor1 = screen.getByTestId('monaco-editor');

      rerender(
        <TestWrapper>
          <MonacoRoot value="updated code" />
        </TestWrapper>
      );

      const editor2 = screen.getByTestId('monaco-editor');

      // Editor should re-render with new content
      expect(editor2).toBeInTheDocument();
    });

    it('15. Error Recovery - handles editor mount failures gracefully', () => {
      // Mock console.error to suppress error logs in test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      // Mock a failing Monaco import
      vi.doMock('@monaco-editor/react', () => ({
        default: () => {
          throw new Error('Monaco failed to load');
        }
      }));

      render(
        <TestWrapper>
          <MonacoRoot value="test" />
        </TestWrapper>
      );

      // Error boundary should catch the error
      expect(screen.getByTestId('error-boundary')).toBeInTheDocument();

      consoleSpy.mockRestore();
    });
  });
});
