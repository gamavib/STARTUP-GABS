import axios from 'axios';

const API_BASE_URL = 'http://localhost:8000';

// Interceptor para manejar errores de autenticación globalmente
const apiClient = axios.create({
    baseURL: API_BASE_URL,
});

apiClient.interceptors.response.use(
    (response) => response,
    (error) => {
        if (error.response && error.response.status === 401) {
            console.error("SESS_EXPIRED: Token expirado o inválido. Redirigiendo al login...");
            localStorage.removeItem('token');
            localStorage.removeItem('company_id');
            window.location.href = '/'; // Redirige a la página de login
        }
        return Promise.reject(error);
    }
);

export const api = {
    login: async (email, password) => {
        const formData = new FormData();
        formData.append('username', email);
        formData.append('password', password);

        const response = await apiClient.post('/token', formData, {
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded'
            }
        });
        return response.data;
    },
    uploadCsv: async (formData, token) => {
        const response = await apiClient.post('/upload-csv', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
                'Authorization': `Bearer ${token}`
            }
        });
        return response.data;
    },
    getActuarialAnalysis: async (ramo = '', token) => {
        const response = await apiClient.get('/actuarial/analysis', {
            params: { ramo },
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    getProjections: async (params, token) => {
        const response = await apiClient.get('/actuarial/projections', {
            params: params,
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    getContractDraft: async (params, token) => {
        const response = await apiClient.get('/actuarial/contract-draft', {
            params: params,
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    getTriangleData: async ({ ramo = '', metric = 'paid', token }) => {
        const response = await apiClient.get('/actuarial/triangle', {
            params: { ramo, metric },
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    calculateCustomIBNR: async ({ ramo = '', metric = 'paid', customLdfs = [], severityAdj = 1.0, token }) => {
        const response = await apiClient.post('/actuarial/calculate-ibnr', null, {
            params: { ramo, metric, custom_ldfs: customLdfs, severity_adj: severityAdj },
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    getRamos: async (token) => {
        const response = await apiClient.get('/actuarial/ramos', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    getBacktestingData: async ({ ramo, method, token }) => {
        const response = await apiClient.get('/actuarial/backtesting', {
            params: { ramo, method },
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    renewContract: async ({ ramo, method, token }) => {
        const response = await apiClient.post('/actuarial/renew', null, {
            params: { ramo, method },
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    },
    activateContract: async ({ ramo, contract_type, priority, limit, cession_pct, token }) => {
        const response = await apiClient.post('/actuarial/contracts/activate', null, {
            params: { ramo, contract_type, priority, limit, cession_pct },
            headers: { 'Authorization': `Bearer ${token}` }
        });
        return response.data;
    }
};
