// queryClient.js
// ----------------------------------------------------------------------------
// Centralised TanStack Query client configuration.
// Placing this in its own module avoids import cycles and lets tests obtain the
// same singleton instance with `import { queryClient } from 'src/queryClient'`.
// ----------------------------------------------------------------------------

import { QueryClient } from "@tanstack/react-query";

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      // Disable refetch on window focus to avoid noisy network traffic while
      // we are migrating existing code. Teams can enable later if desired.
      refetchOnWindowFocus: false,
      retry: 1, // simple retry for transient errors – we have global axios retry too
    },
    mutations: {
      retry: 0,
    },
  },
});
