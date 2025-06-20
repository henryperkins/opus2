/* eslint-disable */
// hooks/useChatFlows.js
// Integration hook for the three key chat flows

import { useState, useCallback, useRef } from 'react';
import { flowConfigs, defaultChatSettings } from '../config/chat-settings';
import knowledgeAPI from '../api/knowledge';
import modelsAPI from '../api/models';
import renderingAPI from '../api/rendering';
import analyticsAPI from '../api/analytics';

export const useChatFlows = (settings = defaultChatSettings) => {
    const [flowState, setFlowState] = useState({
        knowledgeBase: { step: null, data: null, loading: false },
        modelSelection: { step: null, data: null, loading: false },
        responseRendering: { step: null, data: null, loading: false }
    });

    const [metrics, setMetrics] = useState({
        totalRequests: 0,
        successfulRequests: 0,
        averageResponseTime: 0,
        knowledgeHitRate: 0
    });

    const abortControllerRef = useRef(null);

    // Knowledge Base Flow: User types → Query analysis → Knowledge retrieval → Context injection → Model call → Response with citations
    const executeKnowledgeFlow = useCallback(async (query, projectId) => {
        const startTime = Date.now();

        try {
            setFlowState(prev => ({
                ...prev,
                knowledgeBase: { step: 'queryAnalysis', data: null, loading: true }
            }));

            // Step 1: Query Analysis
            const analysisResult = await knowledgeAPI.analyzeQuery(query, projectId);

            setFlowState(prev => ({
                ...prev,
                knowledgeBase: { step: 'knowledgeRetrieval', data: analysisResult, loading: true }
            }));

            // Step 2: Knowledge Retrieval
            const knowledgeResults = await knowledgeAPI.retrieveKnowledge(analysisResult, projectId, settings.knowledge);

            setFlowState(prev => ({
                ...prev,
                knowledgeBase: { step: 'contextInjection', data: knowledgeResults, loading: true }
            }));

            // Step 3: Context Injection
            const contextualizedQuery = await knowledgeAPI.injectContext(query, knowledgeResults, settings.knowledge);

            setFlowState(prev => ({
                ...prev,
                knowledgeBase: { step: 'modelCall', data: contextualizedQuery, loading: true }
            }));

            // Step 4: Model Call (delegates to model selection flow)
            const modelResponse = await executeModelSelectionFlow(contextualizedQuery, analysisResult.taskType);

            setFlowState(prev => ({
                ...prev,
                knowledgeBase: { step: 'responseWithCitations', data: modelResponse, loading: true }
            }));

            // Step 5: Response with Citations
            const finalResponse = await knowledgeAPI.addCitations(modelResponse, knowledgeResults, settings.knowledge.citationStyle);

            setFlowState(prev => ({
                ...prev,
                knowledgeBase: { step: 'complete', data: finalResponse, loading: false }
            }));

            // Update metrics
            const responseTime = Date.now() - startTime;
            await updateMetrics({
                responseTime,
                success: true,
                knowledgeHit: knowledgeResults.length > 0,
                projectId,
                flowType: 'knowledge'
            });

            return finalResponse;

        } catch (error) {
            setFlowState(prev => ({
                ...prev,
                knowledgeBase: { step: 'error', data: error, loading: false }
            }));

            await updateMetrics({ success: false, projectId, flowType: 'knowledge' });
            throw error;
        }
    }, [settings]);

    // Model Selection Flow: Task detection → Model capability matching → Cost/performance evaluation → Model selection → Fallback handling
    const executeModelSelectionFlow = useCallback(async (query, taskType) => {
        try {
            setFlowState(prev => ({
                ...prev,
                modelSelection: { step: 'taskDetection', data: null, loading: true }
            }));

            // Step 1: Task Detection (may be provided or auto-detected)
            const detectedTask = taskType || await modelsAPI.detectTask(query);

            setFlowState(prev => ({
                ...prev,
                modelSelection: { step: 'capabilityMatching', data: detectedTask, loading: true }
            }));

            // Step 2: Model Capability Matching
            const capableModels = await modelsAPI.matchCapabilities(detectedTask, settings.models);

            setFlowState(prev => ({
                ...prev,
                modelSelection: { step: 'costPerformanceEvaluation', data: capableModels, loading: true }
            }));

            // Step 3: Cost/Performance Evaluation
            const evaluatedModels = await modelsAPI.evaluateCostPerformance(capableModels, settings.models);

            setFlowState(prev => ({
                ...prev,
                modelSelection: { step: 'modelSelection', data: evaluatedModels, loading: true }
            }));

            // Step 4: Model Selection
            let selectedModel = modelsAPI.selectOptimalModel(evaluatedModels, settings.models);

            try {
                const response = await modelsAPI.callModel(selectedModel, query);

                setFlowState(prev => ({
                    ...prev,
                    modelSelection: { step: 'complete', data: { model: selectedModel, response }, loading: false }
                }));

                return { model: selectedModel, response };

            } catch (modelError) {
                // Step 5: Fallback Handling
                setFlowState(prev => ({
                    ...prev,
                    modelSelection: { step: 'fallbackHandling', data: modelError, loading: true }
                }));

                const fallbackResponse = await modelsAPI.handleFallback(selectedModel, query, settings.models.fallbacks);

                setFlowState(prev => ({
                    ...prev,
                    modelSelection: { step: 'complete', data: fallbackResponse, loading: false }
                }));

                return fallbackResponse;
            }

        } catch (error) {
            setFlowState(prev => ({
                ...prev,
                modelSelection: { step: 'error', data: error, loading: false }
            }));
            throw error;
        }
    }, [settings]);

    // Response Rendering Flow: Stream reception → Format detection → Progressive rendering → Interactive element injection → Action binding
    const executeRenderingFlow = useCallback(async (responseData, onStreamUpdate) => {
        try {
            setFlowState(prev => ({
                ...prev,
                responseRendering: { step: 'streamReception', data: null, loading: true }
            }));

            // Step 1: Stream Reception
            const streamProcessor = renderingAPI.createStreamProcessor(responseData, settings.rendering);

            setFlowState(prev => ({
                ...prev,
                responseRendering: { step: 'formatDetection', data: streamProcessor, loading: true }
            }));

            // Step 2: Format Detection
            const formatInfo = await renderingAPI.detectFormats(streamProcessor.buffer);

            setFlowState(prev => ({
                ...prev,
                responseRendering: { step: 'progressiveRendering', data: formatInfo, loading: true }
            }));

            // Step 3: Progressive Rendering
            const renderedChunks = [];
            await streamProcessor.process(async (chunk) => {
                const renderedChunk = await renderingAPI.renderChunk(chunk, formatInfo, settings.rendering);
                renderedChunks.push(renderedChunk);
                onStreamUpdate?.(renderedChunks);
            });

            setFlowState(prev => ({
                ...prev,
                responseRendering: { step: 'interactiveElementInjection', data: renderedChunks, loading: true }
            }));

            // Step 4: Interactive Element Injection
            const interactiveElements = await renderingAPI.injectInteractiveElements(renderedChunks, formatInfo);

            setFlowState(prev => ({
                ...prev,
                responseRendering: { step: 'actionBinding', data: interactiveElements, loading: true }
            }));

            // Step 5: Action Binding
            const boundElements = await renderingAPI.bindActions(interactiveElements);

            setFlowState(prev => ({
                ...prev,
                responseRendering: { step: 'complete', data: boundElements, loading: false }
            }));

            return boundElements;

        } catch (error) {
            setFlowState(prev => ({
                ...prev,
                responseRendering: { step: 'error', data: error, loading: false }
            }));
            throw error;
        }
    }, [settings]);

    // Utility functions (these would be implemented based on your backend APIs)
    const analyzeQuery = async (query) => {
        // Mock implementation - replace with actual API call
        return {
            intent: 'code_analysis',
            taskType: 'coding',
            complexity: 'medium',
            keywords: query.split(' ').filter(word => word.length > 3)
        };
    };

    const retrieveKnowledge = async (analysis, projectId, knowledgeSettings) => {
        // Mock implementation - replace with actual knowledge base API
        return [
            { id: '1', content: 'Relevant context 1', confidence: 0.9 },
            { id: '2', content: 'Relevant context 2', confidence: 0.8 }
        ].filter(item => item.confidence >= knowledgeSettings.minConfidence)
            .slice(0, knowledgeSettings.maxContextDocs);
    };

    const injectContext = async (query, knowledge, settings) => {
        const contextPrefix = knowledge.map(k => k.content).join('\n\n');
        return `Context:\n${contextPrefix}\n\nQuery: ${query}`;
    };

    const addCitations = async (response, knowledge, citationStyle) => {
        // Add citations based on style preference
        if (citationStyle === 'inline') {
            return {
                ...response,
                content: response.response + '\n\nSources: ' + knowledge.map(k => k.id).join(', ')
            };
        }
        return response;
    };

    const detectTask = async (query) => {
        // Simple task detection - enhance with actual ML model
        if (query.includes('code') || query.includes('function')) return 'coding';
        if (query.includes('analyze') || query.includes('explain')) return 'analysis';
        return 'general';
    };

    const matchCapabilities = async (taskType, modelSettings) => {
        // Mock model capability matching
        const models = {
            'gpt-4': { coding: 0.9, analysis: 0.95, creative: 0.8, cost: 0.03 },
            'gpt-3.5-turbo': { coding: 0.8, analysis: 0.85, creative: 0.7, cost: 0.002 },
            'claude-3-sonnet': { coding: 0.85, analysis: 0.9, creative: 0.9, cost: 0.015 }
        };

        return Object.entries(models)
            .filter(([model]) => [modelSettings.default, ...modelSettings.fallbacks].includes(model))
            .map(([model, capabilities]) => ({ model, capabilities }));
    };

    const evaluateCostPerformance = async (models, settings) => {
        return models.map(({ model, capabilities }) => ({
            model,
            capabilities,
            score: (capabilities.coding + capabilities.analysis) / (capabilities.cost * 10),
            withinBudget: capabilities.cost <= (settings.costLimit || 1)
        }));
    };

    const selectOptimalModel = (evaluatedModels, settings) => {
        const withinBudget = evaluatedModels.filter(m => m.withinBudget);
        const candidates = withinBudget.length > 0 ? withinBudget : evaluatedModels;
        return candidates.sort((a, b) => b.score - a.score)[0]?.model || settings.default;
    };

    const callModel = async (model, query) => {
        // Mock API call - replace with actual model API
        return new Promise((resolve) => {
            setTimeout(() => {
                resolve({
                    response: `Response from ${model}: ${query}`,
                    model,
                    timestamp: new Date()
                });
            }, 1000 + Math.random() * 2000);
        });
    };

    const handleFallback = async (failedModel, query, fallbacks) => {
        for (const fallbackModel of fallbacks) {
            if (fallbackModel !== failedModel) {
                try {
                    return await callModel(fallbackModel, query);
                } catch (error) {
                    continue;
                }
            }
        }
        throw new Error('All models failed');
    };

    const createStreamProcessor = (responseData, renderingSettings) => {
        return {
            buffer: responseData.response || '',
            process: async (onChunk) => {
                const chunks = responseData.response.split(' ');
                for (let i = 0; i < chunks.length; i++) {
                    await new Promise(resolve => setTimeout(resolve, 50));
                    await onChunk(chunks.slice(0, i + 1).join(' '));
                }
            }
        };
    };

    const detectFormats = async (content) => {
        return {
            hasCode: /```/.test(content),
            hasMath: /\$\$/.test(content),
            hasDiagrams: /mermaid|graph/.test(content),
            hasInteractive: /\[interactive\]/.test(content)
        };
    };

    const renderChunk = async (chunk, formatInfo, settings) => {
        try {
            const result = await renderingAPI.renderChunk(chunk, formatInfo, settings);

            return {
                content: result.content || chunk,
                formatted: result.formatted || true,
                timestamp: Date.now(),
                type: result.type || 'text',
                metadata: result.metadata || {}
            };
        } catch (error) {
            console.error('Chunk rendering failed:', error);
            return {
                content: chunk,
                formatted: false,
                timestamp: Date.now(),
                type: 'text',
                metadata: {}
            };
        }
    };

    const injectInteractiveElements = async (chunks, formatInfo) => {
        try {
            const result = await renderingAPI.injectInteractiveElements(chunks, formatInfo);

            return result || chunks.map(chunk => ({
                ...chunk,
                interactive: formatInfo?.hasInteractive || false,
                interactiveElements: []
            }));
        } catch (error) {
            console.error('Interactive element injection failed:', error);
            return chunks.map(chunk => ({
                ...chunk,
                interactive: formatInfo?.hasInteractive || false,
                interactiveElements: []
            }));
        }
    };

    const bindActions = async (elements) => {
        try {
            const result = await renderingAPI.bindActions(elements);

            return result || elements.map(element => ({
                ...element,
                actions: element.interactive ? ['copy', 'edit', 'run'] : ['copy'],
                actionHandlers: {}
            }));
        } catch (error) {
            console.error('Action binding failed:', error);
            return elements.map(element => ({
                ...element,
                actions: element.interactive ? ['copy', 'edit', 'run'] : ['copy'],
                actionHandlers: {}
            }));
        }
    };

    const updateMetrics = async (update) => {
        // Update local state
        setMetrics(prev => ({
            totalRequests: prev.totalRequests + 1,
            successfulRequests: prev.successfulRequests + (update.success ? 1 : 0),
            averageResponseTime: update.responseTime
                ? (prev.averageResponseTime + update.responseTime) / 2
                : prev.averageResponseTime,
            knowledgeHitRate: update.knowledgeHit !== undefined
                ? (prev.knowledgeHitRate + (update.knowledgeHit ? 1 : 0)) / 2
                : prev.knowledgeHitRate
        }));

        // Send metrics to analytics API
        try {
            if (update.flowType) {
                await analyticsAPI.trackFlowMetrics({
                    project_id: update.projectId,
                    flow_type: update.flowType,
                    success: update.success,
                    response_time: update.responseTime,
                    knowledge_hit: update.knowledgeHit,
                    timestamp: new Date().toISOString()
                });
            }
        } catch (error) {
            console.warn('Failed to track metrics:', error);
        }
    };

    const resetFlows = useCallback(() => {
        if (abortControllerRef.current) {
            abortControllerRef.current.abort();
        }

        setFlowState({
            knowledgeBase: { step: null, data: null, loading: false },
            modelSelection: { step: null, data: null, loading: false },
            responseRendering: { step: null, data: null, loading: false }
        });
    }, []);

    return {
        flowState,
        metrics,
        executeKnowledgeFlow,
        executeModelSelectionFlow,
        executeRenderingFlow,
        resetFlows
    };
};
