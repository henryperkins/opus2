// Code file management API client for upload, parsing, and retrieval
import client from './client';

export const codeAPI = {
    async uploadFiles(projectId, files, onProgress) {
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));

        const response = await client.post(`/api/code/projects/${projectId}/upload`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data'
            },
            onUploadProgress: (evt) => {
                if (onProgress && evt.total) {
                    const percent = (evt.loaded / evt.total) * 100;
                    onProgress(percent);
                }
            }
        });
        return response.data;
    },

    async getProjectFiles(projectId, params = {}) {
        const response = await client.get(`/api/code/projects/${projectId}/files`, { params });
        return response.data;
    },

    async deleteFile(fileId) {
        const response = await client.delete(`/api/code/files/${fileId}`);
        return response.data;
    },

    async getFileContent(fileId) {
        const response = await client.get(`/api/code/files/${fileId}/content`);
        return response.data;
    },

    async getFileSymbols(fileId) {
        const response = await client.get(`/api/code/files/${fileId}/symbols`);
        return response.data;
    },

    async reindexProject(projectId) {
        const response = await client.post(`/api/code/projects/${projectId}/reindex`);
        return response.data;
    },

    async getIndexingStatus(projectId) {
        const response = await client.get(`/api/code/projects/${projectId}/indexing-status`);
        return response.data;
    },

    async saveCanvasArtifact(projectId, canvasData) {
        const response = await client.post(`/api/code/projects/${projectId}/artifacts/canvas`, {
            name: canvasData.name,
            description: canvasData.description,
            svg_content: canvasData.svgContent,
            shapes: canvasData.shapes,
            annotations: canvasData.annotations,
            metadata: canvasData.metadata
        });
        return response.data;
    },

    async getCanvasArtifacts(projectId) {
        const response = await client.get(`/api/code/projects/${projectId}/artifacts/canvas`);
        return response.data;
    },

    async deleteCanvasArtifact(projectId, artifactId) {
        const response = await client.delete(`/api/code/projects/${projectId}/artifacts/canvas/${artifactId}`);
        return response.data;
    }
};
