// timeline.js – Activity log API client

import client from "./client";

export const timelineAPI = {
  list: (params = {}) =>
    client.get("/api/timeline", { params }).then((r) => r.data),

  /* Fetch timeline events for a single project */
  project: (projectId, params = {}) =>
    client
      .get(`/api/projects/${projectId}/timeline`, { params })
      .then((r) => r.data),
};
