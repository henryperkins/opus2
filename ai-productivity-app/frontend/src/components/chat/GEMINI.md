## Chat Components

This directory contains all the React components related to the chat interface. This is a critical and high-risk area of the application due to its complex state management, real-time interactions, and interconnected components.

### Key Components

*   **`ChatLayout.jsx`**: A responsive layout component that uses `react-resizable-panels` to create a flexible chat interface with a sidebar and an editor panel.
*   **`MessageList.jsx`**: Displays the list of chat messages using `@tanstack/react-virtual` for efficient rendering of long conversations.
*   **`ChatMessage.jsx`**: Renders a single chat message, including the user's avatar, the message content, and any associated actions.
*   **`StreamingMessage.jsx`**: A specialized component for rendering streaming responses from the AI, with a typing indicator and token counter.
*   **`ChatInput.jsx`**: A rich text input component for composing messages, with support for slash commands, file attachments, and keyboard shortcuts.
*   **`EnhancedMessageRenderer.jsx`**: A sophisticated component that renders message content with support for Markdown, code highlighting, math equations (KaTeX), and Mermaid diagrams.
*   **`InteractiveElements.jsx`**: Renders interactive elements within the chat, such as executable code blocks, query builders, and decision trees.
*   **`KnowledgeAssistant.jsx`**: A sidebar component that provides contextual information and suggestions based on the current conversation.
*   **`ModelSwitcher.jsx`**: Allows the user to switch between different AI models.
*   **`RAGStatusIndicator.jsx`**: Displays the status of the Retrieval-Augmented Generation (RAG) system.
*   **`CitationRenderer.jsx`**: Renders citations for RAG responses.

### State Management

The chat components rely on the `useChat` hook (likely defined in `frontend/src/hooks/useChat.js`) to manage the chat state, including the list of messages, the connection state, and the list of typing users. The `useChat` hook, in turn, likely uses the `useWebSocketChannel` hook to handle real-time communication with the backend.

### Component Interaction

The chat components are highly interconnected. For example:

*   `MessageList` renders a list of `ChatMessage` components.
*   `ChatMessage` uses `EnhancedMessageRenderer` to render the message content.
*   `EnhancedMessageRenderer` can render `InteractiveElements`.
*   `ChatInput` sends new messages to the `useChat` hook.
*   `KnowledgeAssistant` provides contextual information to the `ChatInput`.

### Future Development

*   **Adding a new interactive element**: To add a new interactive element, create a new component in this directory and add it to the `renderElement` function in `InteractiveElements.jsx`.
*   **Modifying the chat layout**: To modify the chat layout, update the `ChatLayout.jsx` component.
*   **Changing the message rendering**: To change how messages are rendered, update the `EnhancedMessageRenderer.jsx` component.
*   **Adding a new chat action**: To add a new action to a chat message, update the `ChatMessage.jsx` component and add a new case to the `handleAction` function.
*   **Testing**: Due to the complexity of this directory, it is crucial to write thorough unit and integration tests for any new or modified components. Pay special attention to the interactions between components and the handling of real-time events.
