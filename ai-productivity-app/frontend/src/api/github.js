// Git repository integration API client
import client from './client';

export const repositoryAPI = {
    async connectRepository(projectId, data) {
        const response = await client.post(`/api/projects/${projectId}/repositories`, data);
        return response.data;
    },

    async getRepositories(projectId) {
        const response = await client.get(`/api/projects/${projectId}/repositories`);
        return response.data;
    },

    async syncRepository(projectId, repositoryId) {
        const response = await client.post(`/api/projects/${projectId}/repositories/${repositoryId}/sync`);
        return response.data;
    },

    async disconnectRepository(projectId, repositoryId) {
        const response = await client.delete(`/api/projects/${projectId}/repositories/${repositoryId}`);
        return response.data;
    },

    async getRepositoryStatus(projectId, repositoryId) {
        const response = await client.get(`/api/projects/${projectId}/repositories/${repositoryId}/status`);
        return response.data;
    }
};
