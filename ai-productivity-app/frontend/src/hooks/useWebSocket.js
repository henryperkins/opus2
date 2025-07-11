// useWebSocket.js - Legacy hook redirects to useWebSocketChannel
// This file exists to prevent import errors but functionality has been moved to useWebSocketChannel

import { useWebSocketChannel } from "./useWebSocketChannel";

// Re-export the modern hook for backward compatibility
export const useWebSocket = useWebSocketChannel;
export { useWebSocketChannel };
