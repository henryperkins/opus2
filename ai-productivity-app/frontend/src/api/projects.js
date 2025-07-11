// Project API client for CRUD, filtering, timeline, and status.

import client from "./client";

export const projectAPI = {
  list: (filters = {}) =>
    client.get("/api/projects", { params: filters }).then((r) => r.data),

  get: (id) => client.get(`/api/projects/${id}`).then((r) => r.data),

  create: (data) => client.post("/api/projects", data).then((r) => r.data),

  update: (id, data) =>
    client.put(`/api/projects/${id}`, data).then((r) => r.data),

  delete: (id) => client.delete(`/api/projects/${id}`),

  getTimeline: (id) =>
    client.get(`/api/projects/${id}/timeline`).then((r) => r.data),

  addTimelineEvent: (id, data) =>
    client.post(`/api/projects/${id}/timeline`, data).then((r) => r.data),

  archive: (id) =>
    client.post(`/api/projects/${id}/archive`).then((r) => r.data),

  unarchive: (id) =>
    client.post(`/api/projects/${id}/unarchive`).then((r) => r.data),
};
