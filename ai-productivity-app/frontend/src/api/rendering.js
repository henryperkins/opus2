/* eslint-disable */
// api/rendering.js
// Response rendering and streaming API

import client from './client';

export const renderingAPI = {
    /**
     * Create a streaming processor for real-time response rendering
     * @param {object} responseData - Initial response data
     * @param {object} settings - Rendering settings
     * @returns {object} Stream processor with methods
     */
    createStreamProcessor: (responseData, settings) => {
        return {
            buffer: responseData.response || '',
            settings,

            /**
             * Process stream chunks with callback
             * @param {function} onChunk - Callback for each chunk
             */
            async process(onChunk) {
                // For real streaming, you'd typically use EventSource or WebSocket
                // This simulates chunked processing for now
                const chunks = this.buffer.split(' ');
                const chunkSize = settings.streamingEnabled ? 5 : chunks.length;

                for (let i = 0; i < chunks.length; i += chunkSize) {
                    const chunk = chunks.slice(0, i + chunkSize).join(' ');
                    await new Promise(resolve => setTimeout(resolve, settings.streamingEnabled ? 100 : 0));
                    await onChunk(chunk);
                }
            }
        };
    },

    /**
     * Detect content formats in the response
     * @param {string} content - Response content
     * @returns {Promise<object>} Format detection results
     */
    detectFormats: async (content) => {
        const response = await client.post('/api/rendering/detect-formats', {
            content
        });
        return response.data;
    },

    /**
     * Render a content chunk with appropriate formatting
     * @param {string} chunk - Content chunk
     * @param {object} formatInfo - Format detection results
     * @param {object} settings - Rendering settings
     * @returns {Promise<object>} Rendered chunk
     */
    renderChunk: async (chunk, formatInfo, settings) => {
        const response = await client.post('/api/rendering/render-chunk', {
            chunk,
            format_info: formatInfo,
            syntax_theme: settings.syntaxTheme,
            math_renderer: settings.mathRenderer,
            diagram_renderer: settings.diagramRenderer
        });
        return response.data;
    },

    /**
     * Inject interactive elements into rendered content
     * @param {Array} chunks - Rendered chunks
     * @param {object} formatInfo - Format information
     * @returns {Promise<Array>} Chunks with interactive elements
     */
    injectInteractiveElements: async (chunks, formatInfo) => {
        const response = await client.post('/api/rendering/inject-interactive', {
            chunks,
            format_info: formatInfo
        });
        return response.data;
    },

    /**
     * Bind actions to interactive elements
     * @param {Array} elements - Elements with interactive components
     * @returns {Promise<Array>} Elements with bound actions
     */
    bindActions: async (elements) => {
        const response = await client.post('/api/rendering/bind-actions', {
            elements
        });
        return response.data;
    },

    /**
     * Create a real-time streaming connection
     * @param {string} sessionId - Chat session ID
     * @param {object} options - Streaming options
     * @returns {EventSource} Server-Sent Events stream
     */
    createStream: (sessionId, options = {}) => {
        const params = new URLSearchParams({
            session_id: sessionId,
            ...options
        });

        // Create EventSource for real-time streaming
        const eventSource = new EventSource(
            `/api/rendering/stream?${params}`,
            { withCredentials: true }
        );

        return eventSource;
    },

    /**
     * Process mathematical expressions
     * @param {string} expression - Math expression
     * @param {string} renderer - 'katex' or 'mathjax'
     * @returns {Promise<object>} Rendered math
     */
    renderMath: async (expression, renderer = 'katex') => {
        const response = await client.post('/api/rendering/math', {
            expression,
            renderer
        });
        return response.data;
    },

    /**
     * Process diagram content
     * @param {string} diagramCode - Diagram source code
     * @param {string} type - Diagram type (mermaid, d3, etc.)
     * @returns {Promise<object>} Rendered diagram
     */
    renderDiagram: async (diagramCode, type = 'mermaid') => {
        const response = await client.post('/api/rendering/diagram', {
            code: diagramCode,
            type
        });
        return response.data;
    },

    /**
     * Get rendering capabilities and supported formats
     * @returns {Promise<object>} Supported formats and renderers
     */
    getCapabilities: async () => {
        const response = await client.get('/api/rendering/capabilities');
        return response.data;
    },

    /**
     * Validate content for security (XSS prevention, etc.)
     * @param {string} content - Content to validate
     * @returns {Promise<object>} Validation result
     */
    validateContent: async (content) => {
        const response = await client.post('/api/rendering/validate', {
            content
        });
        return response.data;
    }
};

export default renderingAPI;
