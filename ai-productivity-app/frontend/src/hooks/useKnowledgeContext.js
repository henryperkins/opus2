// useKnowledgeContext.js – helper hook for knowledge-aware chat flows
// ------------------------------------------------------------------
// The hook encapsulates the logic for
//  • analysing a user query (intent detection)
//  • retrieving knowledge documents
//  • injecting citations / context into chat metadata
//  • keeping a local in-memory basket of citations so multiple components
//    (KnowledgeAssistant, KnowledgeContextPanel, ChatPage) stay in sync.

import { useState, useCallback, useMemo } from 'react';
import { useMutation } from '@tanstack/react-query';

const DEFAULT_SETTINGS = {
  autoContext: true,
  maxContextDocs: 5,
  minConfidence: 0.2,
  citationStyle: 'inline', // or 'footnote'
};

export function useKnowledgeChat(projectId, userSettings = {}, knowledgeAPI = null) {
  const settings = useMemo(() => ({ ...DEFAULT_SETTINGS, ...userSettings }), [userSettings]);

  const [citations, setCitations] = useState([]);
  const [currentContext, setCurrentContext] = useState([]);

  // Ensure knowledgeAPI is provided
  if (!knowledgeAPI) {
    console.warn('useKnowledgeChat: knowledgeAPI not provided, hook will have limited functionality');
  }

  // -----------------------------
  // Mutations
  // -----------------------------

  const analyzeMutation = useMutation({
    mutationFn: ({ query }) => {
      if (!knowledgeAPI) throw new Error('Knowledge API not available');
      return knowledgeAPI.analyzeQuery(query, projectId);
    },
  });

  const retrieveMutation = useMutation({
    mutationFn: ({ analysis }) => {
      if (!knowledgeAPI) throw new Error('Knowledge API not available');
      return knowledgeAPI.retrieveKnowledge(analysis, projectId, settings);
    },
  });

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
      if (!knowledgeAPI) {
        console.warn('Knowledge API not available');
        return { contextualisedQuery: query, documents: [] };
      }

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
        // Separate documents and code snippets for UI compatibility
        const relevantDocs = docs.filter(doc => doc.type === 'document' || !doc.type);
        const codeSnippets = docs.filter(doc => doc.type === 'code');
        
        return { 
          contextualisedQuery: contextualised, 
          documents: docs,
          relevantDocs,
          codeSnippets
        };
      }

      // Separate documents and code snippets for UI compatibility
      const relevantDocs = docs.filter(doc => doc.type === 'document' || !doc.type);
      const codeSnippets = docs.filter(doc => doc.type === 'code');
      
      return { 
        contextualisedQuery: query, 
        documents: docs,
        relevantDocs,
        codeSnippets
      };
    },
    [settings, analyzeMutation, retrieveMutation, addToCitations, knowledgeAPI]
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
