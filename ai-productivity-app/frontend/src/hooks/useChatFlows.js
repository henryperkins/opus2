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

    // Direct API calls (replacing mock implementations)
    const analyzeQuery = knowledgeAPI.analyzeQuery;
    const retrieveKnowledge = knowledgeAPI.retrieveKnowledge;
    const injectContext = knowledgeAPI.injectContext;
    const addCitations = knowledgeAPI.addCitations;
    const detectTask = modelsAPI.detectTask;
    const matchCapabilities = modelsAPI.matchCapabilities;
    const evaluateCostPerformance = modelsAPI.evaluateCostPerformance;
    const selectOptimalModel = modelsAPI.selectOptimalModel;
    const callModel = modelsAPI.callModel;
    const handleFallback = modelsAPI.handleFallback;
    const createStreamProcessor = renderingAPI.createStreamProcessor;
    const detectFormats = renderingAPI.detectFormats;
    const renderChunk = renderingAPI.renderChunk;
    const injectInteractiveElements = renderingAPI.injectInteractiveElements;
    const bindActions = renderingAPI.bindActions;

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
