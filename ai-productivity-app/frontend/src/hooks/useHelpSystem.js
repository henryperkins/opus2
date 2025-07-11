import { useState, useCallback } from "react";

/**
 * Hook for managing the integrated help system (tooltips + documentation modal)
 */
export const useHelpSystem = () => {
  const [isDocumentationOpen, setIsDocumentationOpen] = useState(false);
  const [activeDocTab, setActiveDocTab] = useState("overview");

  const openDocumentation = useCallback((tab = "overview") => {
    setActiveDocTab(tab);
    setIsDocumentationOpen(true);
  }, []);

  const closeDocumentation = useCallback(() => {
    setIsDocumentationOpen(false);
  }, []);

  const switchDocTab = useCallback((tab) => {
    setActiveDocTab(tab);
  }, []);

  const openRAGOnboarding = useCallback(() => {
    // This would be implemented when integrating with main app
    console.log("Opening RAG onboarding...");
  }, []);

  return {
    // Documentation modal state
    isDocumentationOpen,
    activeDocTab,
    openDocumentation,
    closeDocumentation,
    switchDocTab,

    // Onboarding
    openRAGOnboarding,

    // Helper functions for specific help topics
    showRAGHelp: () => openDocumentation("rag"),
    showSearchHelp: () => openDocumentation("search"),
    showKnowledgeHelp: () => openDocumentation("knowledge"),
    showChatHelp: () => openDocumentation("chat"),
  };
};

export default useHelpSystem;
