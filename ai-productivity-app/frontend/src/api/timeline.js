// timeline.js – Activity log API client

import client from "./client";

export const timelineAPI = {
  list: (params = {}) =>
    client.get("/api/timeline", { params }).then((r) => r.data),
};
