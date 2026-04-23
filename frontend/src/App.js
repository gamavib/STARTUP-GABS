import React, { useState } from 'react';
import { api } from './services/api';
import ActuarialDashboard from './components/ActuarialDashboard';
import TriangleViewer from './components/TriangleViewer';

function App() {
    const [auth, setAuth] = useState({ email: '', password: '', token: null });
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [file, setFile] = useState(null);
    const [ramo, setRamo] = useState('');
    const [analysisData, setAnalysisData] = useState(null);
    const [projectionData, setProjectionData] = useState(null);
    const [contractDraft, setContractDraft] = useState(null);
    const [severityAdj, setSeverityAdj] = useState(1.0);
    const [capital, setCapital] = useState(1000000);
    const [loading, setLoading] = useState(false);
    const [triangleData, setTriangleData] = useState(null);
    const [showTriangle, setShowTriangle] = useState(false);

    const handleLogin = async () => {
        setLoading(true);
        try {
            const data = await api.login(auth.email, auth.password);
            setAuth(prev => ({ ...prev, token: data.access_token }));
            setIsLoggedIn(true);
        } catch (error) {
            alert('Error de autenticación');
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = async () => {
        if (!file) return alert('Por favor seleccione un archivo');
        setLoading(true);
        const formData = new FormData();
        formData.append('file', file);

        try {
            await api.uploadCsv(formData, auth.token);
            await fetchAnalysis();
            await fetchProjections();
        } catch (error) {
            alert('Error al cargar archivo');
        } finally {
            setLoading(false);
        }
    };

    const fetchAnalysis = async (selectedRamo = ramo) => {
        setLoading(true);
        try {
            const data = await api.getActuarialAnalysis(selectedRamo, auth.token);
            setAnalysisData(data);
        } catch (error) {
            alert('Error al obtener análisis');
        } finally {
            setLoading(false);
        }
    };

    const fetchProjections = async () => {
        setLoading(true);
        try {
            const data = await api.getProjections({
                ramo,
                severity_adj: severityAdj,
                capital: capital
            }, auth.token);
            setProjectionData(data);
        } catch (error) {
            alert('Error al obtener proyecciones');
        } finally {
            setLoading(false);
        }
    };

    const handleDownloadContract = async () => {
        setLoading(true);
        try {
            const data = await api.getContractDraft({
                ramo,
                severity_adj: severityAdj,
                capital: capital
            }, auth.token);
            setContractDraft(data);
        } catch (error) {
            alert('Error al generar borrador');
        } finally {
            setLoading(false);
        }
    };

    const handleViewTriangle = async () => {
        setLoading(true);
        try {
            const data = await api.getTriangleData({
                ramo: ramo,
                metric: 'paid',
                token: auth.token
            });
            setTriangleData(data);
            setShowTriangle(true);
        } catch (error) {
            alert('Error al obtener datos del triángulo');
        } finally {
            setLoading(false);
        }
    };

    if (!isLoggedIn) {
        return (
            <div style={{ minHeight: '100vh', display: 'flex', justifyContent: 'center', alignItems: 'center', backgroundColor: '#f5f7fa' }}>
                <div style={{ backgroundColor: 'white', padding: '40px', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', width: '400px' }}>
                    <h2 style={{ textAlign: 'center', color: '#2c3e50' }}>Acceso SaaS Actuarial</h2>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '15px', marginTop: '20px' }}>
                        <input
                            type="email" placeholder="Email" value={auth.email}
                            onChange={(e) => setAuth({...auth, email: e.target.value})}
                            style={inputStyle}
                        />
                        <input
                            type="password" placeholder="Contraseña" value={auth.password}
                            onChange={(e) => setAuth({...auth, password: e.target.value})}
                            style={inputStyle}
                        />
                        <button onClick={handleLogin} disabled={loading} style={btnStyle}>
                            {loading ? 'Autenticando...' : 'Ingresar'}
                        </button>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div style={{ minHeight: '100vh', backgroundColor: '#f5f7fa', padding: '40px' }}>
            <header style={{ marginBottom: '40px', textAlign: 'center' }}>
                <h1 style={{ color: '#2c3e50' }}>SaaS B2B Optimización de Reaseguro</h1>
                <p style={{ color: '#7f8c8d' }}>Módulo Actuarial y de Proyecciones Estratégicas</p>
                <button onClick={() => setIsLoggedIn(false)} style={{...btnStyle, backgroundColor: '#95a5a6', fontSize: '12px'}}>Cerrar Sesión</button>
            </header>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', marginBottom: '40px', justifyContent: 'center', alignItems: 'center', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <input type="file" onChange={(e) => setFile(e.target.files[0])} />
                    <button onClick={handleUpload} disabled={loading} style={btnStyle}>
                        {loading ? 'Procesando...' : 'Cargar y Analizar'}
                    </button>
                </div>

                <div style={{ borderLeft: '1px solid #ddd', paddingLeft: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>
                    <input
                        type="text"
                        placeholder="Filtrar por ramo..."
                        value={ramo}
                        onChange={(e) => setRamo(e.target.value)}
                        style={inputStyle}
                    />
                    <button onClick={() => fetchAnalysis()} style={btnStyle}>Aplicar Filtro</button>
                </div>

                <div style={{ borderLeft: '1px solid #ddd', paddingLeft: '20px', display: 'flex', gap: '15px', alignItems: 'center' }}>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <label style={{ fontSize: '12px', color: '#7f8c8d' }}>Ajuste Severidad ({severityAdj * 100}%)</label>
                        <input
                            type="range" min="0.5" max="2.0" step="0.05"
                            value={severityAdj} onChange={(e) => setSeverityAdj(parseFloat(e.target.value))}
                        />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                        <label style={{ fontSize: '12px', color: '#7f8c8d' }}>Capital Disponible ($)</label>
                        <input
                            type="number" value={capital} onChange={(e) => setCapital(parseInt(e.target.value))}
                            style={inputStyle}
                        />
                    </div>
                    <button onClick={fetchProjections} disabled={loading} style={btnStyle}>Simular Escenario</button>
                </div>

                <div style={{ borderLeft: '1px solid #ddd', paddingLeft: '20px' }}>
                    <button onClick={handleViewTriangle} disabled={loading} style={btnStyle}>Ver Triángulo</button>
                </div>
            </div>

            <ActuarialDashboard
                data={analysisData}
                projectionData={projectionData}
                contractDraft={contractDraft}
                onDownloadContract={handleDownloadContract}
            />

            {showTriangle && auth.token && (
                <TriangleViewer
                    initialTriangleData={triangleData}
                    initialRamo={ramo}
                    token={auth.token}
                    onClose={() => setShowTriangle(false)}
                />
            )}
        </div>
    );
}

const btnStyle = {
    padding: '8px 16px',
    backgroundColor: '#3498db',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: 'bold'
};

const inputStyle = {
    padding: '8px',
    borderRadius: '4px',
    border: '1px solid #ddd'
};

export default App;
