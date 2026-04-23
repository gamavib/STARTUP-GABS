import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

export const api = {
    login: async (email, password) => {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);

        const response = await axios.post(`${API_BASE_URL}/token`, formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });
        return response.data;
    },
    uploadCsv: async (formData, token) => {
        const response = await axios.post(`${API_BASE_URL}/upload-csv`, formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                'Authorization': `Bearer ${token}`
            }
        });
        return response.data;
    },
    getActuarialAnalysis: async (ramo = '', token) => {
        const response = await axios.get(`${API_BASE_URL}/actuarial/analysis`, {
            params: { ramo },
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    getProjections: async (params, token) => {
        const response = await axios.get(`${API_BASE_URL}/actuarial/projections`, {
            params: params,
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    getContractDraft: async (params, token) => {
        const response = await axios.get(`${API_BASE_URL}/actuarial/contract-draft`, {
            params: params,
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    }
};
