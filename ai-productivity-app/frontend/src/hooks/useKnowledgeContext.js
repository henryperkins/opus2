// useKnowledgeContext.js – helper hook for knowledge-aware chat flows
// ------------------------------------------------------------------
// The hook encapsulates the logic for
//  • analysing a user query (intent detection)
//  • retrieving knowledge documents
//  • injecting citations / context into chat metadata
//  • keeping a local in-memory basket of citations so multiple components
//    (KnowledgeAssistant, KnowledgeContextPanel, ChatPage) stay in sync.

import { useState, useCallback, useMemo } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { knowledgeAPI } from '../api/knowledge';

const DEFAULT_SETTINGS = {
  autoContext: true,
  maxContextDocs: 5,
  minConfidence: 0.2,
  citationStyle: 'inline', // or 'footnote'
};

export function useKnowledgeChat(projectId, userSettings = {}) {
  const settings = { ...DEFAULT_SETTINGS, ...userSettings };

  const [citations, setCitations] = useState([]);
  const [currentContext, setCurrentContext] = useState([]);

  const queryClient = useQueryClient();

  // -----------------------------
  // Mutations
  // -----------------------------

  const analyzeMutation = useMutation(({ query }) =>
    knowledgeAPI.analyzeQuery(query, projectId)
  );

  const retrieveMutation = useMutation(({ analysis }) =>
    knowledgeAPI.retrieveKnowledge(analysis, projectId, settings)
  );

  // -----------------------------
  // Helpers
  // -----------------------------

  const addToCitations = useCallback((docs) => {
    setCitations((prev) => {
      const merged = [...prev];
      docs.forEach((d) => {
        if (!merged.find((m) => m.id === d.id)) merged.push(d);
      });
      return merged;
    });
    return docs.map((d) => ({ id: d.id, title: d.title }));
  }, []);

  const clearCitations = () => setCitations([]);

  const buildContextForQuery = useCallback(
    async (query) => {
      // 1) Analyse intent
      const analysis = await analyzeMutation.mutateAsync({ query });

      // 2) Retrieve matching docs
      const docs = await retrieveMutation.mutateAsync({ analysis });

      // 3) Update local context + citations
      setCurrentContext(docs);
      addToCitations(docs);

      // 4) Optionally inject context into the query
      if (settings.autoContext) {
        const contextualised = await knowledgeAPI.injectContext(
          query,
          docs,
          settings
        );
        return { contextualisedQuery: contextualised, documents: docs };
      }

      return { contextualisedQuery: query, documents: docs };
    },
    [projectId, settings, analyzeMutation, retrieveMutation, addToCitations]
  );

  const value = useMemo(
    () => ({
      analyzeMutation,
      retrieveMutation,
      buildContextForQuery,
      addToCitations,
      clearCitations,
      citations,
      currentContext,
    }),
    [
      analyzeMutation,
      retrieveMutation,
      buildContextForQuery,
      addToCitations,
      citations,
      currentContext,
    ]
  );

  return value;
}
