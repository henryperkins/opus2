// src/test/server.js – MSW setup for Vitest

import { http, HttpResponse } from "msw";
import { setupServer } from "msw/node";

let messageCounter = 0;

export const handlers = [
  // Auth-me: unauthenticated by default unless overridden in tests
  http.get("/api/auth/me", () => {
    return HttpResponse.json(null, { status: 401 });
  }),

  // Create chat session
  http.post("/api/chat/sessions", () => {
    return HttpResponse.json({ id: 123, project_id: 1 });
  }),

  // Messages list (empty)
  http.get("/api/chat/sessions/:id/messages", () => {
    return HttpResponse.json([]);
  }),

  // Project details by id
  http.get("/api/projects/:id", ({ params }) => {
    const { id } = params;
    // Minimal project payload – extend if future tests need extra fields
    return HttpResponse.json({ id: Number(id), name: "Project" });
  }),

  // Send message
  http.post("/api/chat/sessions/:id/messages", async ({ request }) => {
    const { content } = await request.json();
    messageCounter += 1;
    return HttpResponse.json({ id: messageCounter, content });
  }),

  // Patch / Delete handlers for completeness
  http.patch("/api/chat/messages/:id", async ({ request, params }) => {
    const { content } = await request.json();
    return HttpResponse.json({ id: Number(params.id), content });
  }),

  http.delete("/api/chat/messages/:id", () => {
    return new HttpResponse(null, { status: 204 });
  }),
];

export const server = setupServer(...handlers);
