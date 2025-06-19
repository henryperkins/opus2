// frontend/src/api/config.js
import client from './client';

const configAPI = {
    async getConfig() {
        const response = await client.get('/api/config');
        return response.data;
    },
};

export default configAPI;
