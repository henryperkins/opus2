// src/test/server.js – MSW setup for Vitest

import { rest } from 'msw';
import { setupServer } from 'msw/node';

let messageCounter = 0;

export const handlers = [
  // Auth-me: unauthenticated by default unless overridden in tests
  rest.get('/api/auth/me', (_req, res, ctx) => res(ctx.status(401))),

  // Create chat session
  rest.post('/api/chat/sessions', (_req, res, ctx) =>
    res(
      ctx.status(200),
      ctx.json({ id: 123, project_id: 1 })
    )
  ),

  // Messages list (empty)
  rest.get('/api/chat/sessions/:id/messages', (_req, res, ctx) =>
    res(ctx.status(200), ctx.json([]))
  ),

  // Send message
  rest.post('/api/chat/sessions/:id/messages', async (req, res, ctx) => {
    const { content } = await req.json();
    messageCounter += 1;
    return res(
      ctx.status(200),
      ctx.json({ id: messageCounter, content })
    );
  }),

  // Patch / Delete handlers for completeness
  rest.patch('/api/chat/messages/:id', async (req, res, ctx) => {
    const { content } = await req.json();
    return res(ctx.status(200), ctx.json({ id: Number(req.params.id), content }));
  }),

  rest.delete('/api/chat/messages/:id', (_req, res, ctx) => res(ctx.status(204))),
];

export const server = setupServer(...handlers);
