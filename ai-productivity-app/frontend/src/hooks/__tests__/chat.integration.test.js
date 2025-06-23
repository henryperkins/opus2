import { describe, it, expect, beforeEach, vi } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import { QueryClientProvider } from '@tanstack/react-query';
import { queryClient } from '../../queryClient';
import { useChat } from '../useChat';

// Mock WebSocket using mock-socket
import { Server } from 'mock-socket';

function createWsServer(sessionId) {
  const wsUrl = `ws://localhost/api/chat/ws/sessions/${sessionId}`;
  const server = new Server(wsUrl);
  return { server, wsUrl };
}

describe('useChat integration', () => {
  beforeEach(() => {
    queryClient.clear();
  });

  it('send → edit → delete flow', async () => {
    const sessionId = 123;
    const { server } = createWsServer(sessionId);

    // Echo message back when send_mutation triggers REST call simulation is done via MSW; Here we simulate WS broadcast
    server.on('connection', (socket) => {
      socket.on('message', (data) => {
        const parsed = JSON.parse(data);
        if (parsed.type === 'typing') return;
      });
    });

    const wrapper = ({ children }) => (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );

    const { result } = renderHook(() => useChat(1, sessionId), { wrapper });

    // Wait for history fetch
    await new Promise((r) => setTimeout(r, 10));

    // Send message
    await act(async () => {
      await result.current.sendMessage('hi', {});
    });

    expect(result.current.messages.length).toBe(1);

    const msgId = result.current.messages[0].id;

    // Edit
    await act(async () => {
      await result.current.editMessage(msgId, 'edited');
    });

    expect(result.current.messages[0].content).toBe('edited');

    // Delete
    await act(async () => {
      await result.current.deleteMessage(msgId);
    });

    expect(result.current.messages.length).toBe(0);
    server.close();
  });
});
