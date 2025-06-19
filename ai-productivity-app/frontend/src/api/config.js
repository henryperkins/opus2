// frontend/src/api/config.js
import client from './client';

const configAPI = {
    async getConfig() {
        const response = await client.get('/api/config');
        return response.data;
    },
    
    async updateModelConfig(config) {
        const response = await client.put('/api/config/model', config);
        return response.data;
    },
    
    async testModelConfig(config) {
        const response = await client.post('/api/config/test', config);
        return response.data;
    },
    
    async getAvailableModels() {
        const response = await client.get('/api/config/models');
        return response.data;
    },
};

export { configAPI };
export default configAPI;
