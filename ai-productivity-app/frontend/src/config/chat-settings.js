/* eslint-disable */
// config/chat-settings.js
// Configuration schema for the AI Productivity App chat system

export const defaultChatSettings = {
    knowledge: {
        autoContext: true,
        maxContextDocs: 10,
        minConfidence: 0.7,
        citationStyle: 'inline' // 'inline' | 'footnote'
    },
    models: {
        default: 'gpt-4',
        fallbacks: ['gpt-3.5-turbo', 'claude-3-sonnet'],
        autoSwitch: true,
        costLimit: 0.10 // dollars per request
    },
    rendering: {
        streamingEnabled: true,
        syntaxTheme: 'oneDark',
        mathRenderer: 'katex', // 'katex' | 'mathjax'
        diagramRenderer: 'mermaid' // 'mermaid' | 'd3'
    },
    quality: {
        trackResponses: true,
        feedbackEnabled: true,
        autoRating: true,
        qualityThreshold: 0.8
    },
    performance: {
        responseTimeout: 30000,
        retryAttempts: 3,
        cacheEnabled: true,
        prefetchContext: true
    }
};

// Validation schema
export const validateChatSettings = (settings) => {
    const errors = [];

    // Knowledge validation
    if (settings.knowledge?.maxContextDocs < 1 || settings.knowledge?.maxContextDocs > 50) {
        errors.push('maxContextDocs must be between 1 and 50');
    }

    if (settings.knowledge?.minConfidence < 0 || settings.knowledge?.minConfidence > 1) {
        errors.push('minConfidence must be between 0 and 1');
    }

    // Models validation
    if (!settings.models?.default) {
        errors.push('Default model must be specified');
    }

    if (settings.models?.costLimit && (settings.models.costLimit < 0 || settings.models.costLimit > 10)) {
        errors.push('costLimit must be between 0 and 10 dollars');
    }

    // Rendering validation
    const validSyntaxThemes = ['oneDark', 'oneLight', 'vsDark', 'vsLight'];
    if (settings.rendering?.syntaxTheme && !validSyntaxThemes.includes(settings.rendering.syntaxTheme)) {
        errors.push(`syntaxTheme must be one of: ${validSyntaxThemes.join(', ')}`);
    }

    return {
        isValid: errors.length === 0,
        errors
    };
};

// Settings merge utility
export const mergeChatSettings = (userSettings, defaultSettings = defaultChatSettings) => {
    return {
        knowledge: { ...defaultSettings.knowledge, ...userSettings.knowledge },
        models: { ...defaultSettings.models, ...userSettings.models },
        rendering: { ...defaultSettings.rendering, ...userSettings.rendering },
        quality: { ...defaultSettings.quality, ...userSettings.quality },
        performance: { ...defaultSettings.performance, ...userSettings.performance }
    };
};

// Flow configurations
export const flowConfigs = {
    knowledgeBase: {
        // User types → Query analysis → Knowledge retrieval → Context injection → Model call → Response with citations
        steps: [
            'queryAnalysis',
            'knowledgeRetrieval',
            'contextInjection',
            'modelCall',
            'responseWithCitations'
        ],
        timeouts: {
            queryAnalysis: 2000,
            knowledgeRetrieval: 5000,
            contextInjection: 1000,
            modelCall: 30000,
            responseWithCitations: 1000
        }
    },

    modelSelection: {
        // Task detection → Model capability matching → Cost/performance evaluation → Model selection → Fallback handling
        steps: [
            'taskDetection',
            'capabilityMatching',
            'costPerformanceEvaluation',
            'modelSelection',
            'fallbackHandling'
        ],
        criteria: {
            taskTypes: ['coding', 'analysis', 'creative', 'factual', 'reasoning'],
            capabilities: ['speed', 'accuracy', 'creativity', 'cost'],
            maxCostPerToken: 0.0001
        }
    },

    responseRendering: {
        // Stream reception → Format detection → Progressive rendering → Interactive element injection → Action binding
        steps: [
            'streamReception',
            'formatDetection',
            'progressiveRendering',
            'interactiveElementInjection',
            'actionBinding'
        ],
        bufferSizes: {
            streamChunk: 256,
            renderBuffer: 1024,
            interactiveDelay: 500
        }
    }
};

export default {
    defaultChatSettings,
    validateChatSettings,
    mergeChatSettings,
    flowConfigs
};
