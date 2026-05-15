import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { api } from './services/api';
import ActuarialDashboard from './components/ActuarialDashboard';
import TriangleViewer from './components/TriangleViewer';
import RenewalViewer from './components/RenewalViewer';
import BacktestingViewer from './components/BacktestingViewer';

function App() {
    const [auth, setAuth] = useState({ email: '', password: '', token: null, role: null });
    const [isLoggedIn, setIsLoggedIn] = useState(false);
    const [file, setFile] = useState(null);
    const [ramo, setRamo] = useState('');
    const [contractDraft, setContractDraft] = useState(null);
    const [severityAdj, setSeverityAdj] = useState(1.0);
    const [capital, setCapital] = useState(1000000);
    const [loading, setLoading] = useState(false);
    const [triangleData, setTriangleData] = useState(null);
    const [activeTab, setActiveTab] = useState('executive');
    const [validationData, setValidationData] = useState(null);
    const [renewalData, setRenewalData] = useState(null);
    const [newUser, setNewUser] = useState({ email: '', password: '', role: 'user' });
    const [uploadStatus, setUploadStatus] = useState('idle'); // 'idle', 'uploading', 'success', 'error'
    const [uploadMessage, setUploadMessage] = useState('');
    const [isMounted, setIsMounted] = useState(false);
    const queryClient = useQueryClient();
    const fileInputRef = useRef(null);

    useEffect(() => {
        setIsMounted(true);
        const checkSession = async () => {
            const token = localStorage.getItem('token');
            if (token) {
                setLoading(true);
                try {
                    const user = await api.verifySession(token);
                    setAuth(prev => ({ ...prev, token, role: user.role }));
                    setIsLoggedIn(true);
                } catch (error) {
                    console.error("Session invalid, clearing storage");
                    localStorage.removeItem('token');
                    localStorage.removeItem('company_id');
                    setIsLoggedIn(false);
                } finally {
                    setLoading(false);
                }
            }
        };
        checkSession();
    }, []);

    const { data: queryRamos, isLoading: loadingRamos } = useQuery({
        queryKey: ['ramos', auth.token],
        queryFn: () => api.getRamos(auth.token),
        enabled: !!auth.token,
    });

    const { data: queryAnalysis, isLoading: loadingAnalysis } = useQuery({
        queryKey: ['analysis', auth.token, ramo],
        queryFn: () => api.getActuarialAnalysis(ramo, auth.token),
        enabled: !!auth.token,
    });

    const { data: queryProjections, isLoading: loadingProjections } = useQuery({
        queryKey: ['projections', auth.token, ramo, severityAdj, capital],
        queryFn: () => api.getProjections({ ramo, severity_adj: severityAdj, capital }, auth.token),
        enabled: !!auth.token,
    });

    const handleLogin = async () => {
        setLoading(true);
        try {
            const data = await api.login(auth.email, auth.password);
            const token = data.access_token;
            setAuth(prev => ({ ...prev, token: token, role: data.role }));
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
        setUploadStatus('uploading');
        setUploadMessage('Subiendo archivo...');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const result = await api.uploadCsv(formData, auth.token);
            if (result.status === 'success') {
                setUploadStatus('success');
                setUploadMessage(result.message);
                // Invalidate TanStack Query caches
                await queryClient.invalidateQueries({ queryKey: ['analysis'] });
                await queryClient.invalidateQueries({ queryKey: ['projections'] });
                await queryClient.invalidateQueries({ queryKey: ['ramos'] });
            } else {
                setUploadStatus('error');
                setUploadMessage(`Error: ${result.errors?.join(', ') || 'Carga fallida'}`);
            }
        } catch (error) {
            setUploadStatus('error');
            setUploadMessage('Error crítico al conectar con el servidor');
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

            if (data.error) {
                alert(`Error actuarial: ${data.error}`);
                return;
            }

            setContractDraft(data);
        } catch (error) {
            alert('Error al generar borrador: ' + (error.response?.data?.detail || error.message));
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
            setActiveTab('actuarial');
        } catch (error) {
            alert('Error al obtener datos del triángulo');
        } finally {
            setLoading(false);
        }
    };

    const fetchValidation = async () => {
        setLoading(true);
        try {
            const data = await api.getBacktestingData({
                ramo,
                method: 'chain_ladder',
                token: auth.token
            });
            setValidationData(data);
        } catch (error) {
            console.error("Error fetching validation data:", error);
        } finally {
            setLoading(false);
        }
    };

    const fetchRenewal = async () => {
        setLoading(true);
        try {
            const data = await api.renewContract({
                ramo,
                method: 'chain_ladder',
                token: auth.token
            });
            setRenewalData(data);
        } catch (error) {
            console.error("Error fetching renewal data:", error);
        } finally {
            setLoading(false);
        }
    };

    const handleCreateUser = async () => {
        if (!newUser.email || !newUser.password) return alert('Email y contraseña son obligatorios');
        setLoading(true);
        try {
            await api.createUser({
                email: newUser.email,
                password: newUser.password,
                role: newUser.role,
                token: auth.token
            });
            alert('Usuario creado exitosamente');
            setNewUser({ email: '', password: '', role: 'user' });
        } catch (error) {
            alert('Error al crear usuario: ' + (error.response?.data?.detail || error.message));
        } finally {
            setLoading(false);
        }
    };

    const renderContent = () => {
        if (!isMounted) return <div style={{textAlign: 'center', padding: '40px'}}>Cargando aplicación...</div>;

        switch (activeTab) {
            case 'executive':
                return (
                    <ActuarialDashboard
                        data={queryAnalysis}
                        projectionData={queryProjections}
                        contractDraft={contractDraft}
                        onDownloadContract={handleDownloadContract}
                    />
                );
            case 'actuarial':
                return (
                    <TriangleViewer
                        initialTriangleData={triangleData}
                        initialRamo={ramo}
                        token={auth.token}
                        onRamoChange={(newRamo) => setRamo(newRamo)}
                    />
                );
            case 'validation':
                return (
                    <div style={{ minHeight: '400px' }}>
                        {validationData && Array.isArray(validationData) ? (
                            <BacktestingViewer
                                data={validationData}
                                loading={loading}
                            />
                        ) : (
                            <div style={{ textAlign: 'center', padding: '40px', color: '#7f8c8d' }}>
                                {loading ? 'Cargando datos de validación...' : 'No hay datos de validación disponibles o el formato es incorrecto.'}
                            </div>
                        )}
                    </div>
                );
            case 'renewal':
                return (
                    <RenewalViewer
                        data={renewalData}
                        token={auth.token}
                        ramo={ramo}
                        onActivate={() => {
                            setActiveTab('executive');
                            fetchRenewal();
                        }}
                    />
                );
            case 'admin':
                return (
                    <div style={{ backgroundColor: 'white', padding: '30px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)', maxWidth: '600px', margin: '0 auto' }}>
                        <h2 style={{ color: '#2c3e50', marginBottom: '20px' }}>Gestión de Usuarios</h2>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '15px' }}>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                <label style={{ fontSize: '14px', color: '#7f8c8d' }}>Email del nuevo usuario</label>
                                <input
                                    type="email" placeholder="ejemplo@correo.com"
                                    value={newUser.email} onChange={(e) => setNewUser({...newUser, email: e.target.value})}
                                    style={inputStyle}
                                />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                <label style={{ fontSize: '14px', color: '#7f8c8d' }}>Contraseña</label>
                                <input
                                    type="password" placeholder="********"
                                    value={newUser.password} onChange={(e) => setNewUser({...newUser, password: e.target.value})}
                                    style={inputStyle}
                                />
                            </div>
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                                <label style={{ fontSize: '14px', color: '#7f8c8d' }}>Rol</label>
                                <select
                                    value={newUser.role} onChange={(e) => setNewUser({...newUser, role: e.target.value})}
                                    style={inputStyle}
                                >
                                    <option value="user">Usuario</option>
                                    <option value="admin">Administrador</option>
                                </select>
                            </div>
                            <button onClick={handleCreateUser} disabled={loading} style={{...btnStyle, marginTop: '10px'}}>
                                {loading ? 'Creando...' : 'Crear Usuario'}
                            </button>
                        </div>
                    </div>
                );
            default:
                return null;
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

            <div style={{
                display: 'flex',
                justifyContent: 'center',
                gap: '10px',
                marginBottom: '30px',
                borderBottom: '2px solid #ddd',
                paddingBottom: '10px'
            }}>
                <button
                    onClick={() => setActiveTab('executive')}
                    style={{
                        ...tabStyle(activeTab === 'executive'),
                        padding: '10px 25px',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                        borderRadius: '8px 8px 0 0',
                        transition: 'all 0.3s ease',
                        backgroundColor: activeTab === 'executive' ? '#3498db' : 'transparent',
                        color: activeTab === 'executive' ? 'white' : '#7f8c8d',
                        border: '1px solid #ddd',
                        borderBottom: activeTab === 'executive' ? '2px solid #3498db' : '1px solid #ddd',
                        boxShadow: activeTab === 'executive' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
                    }}
                >
                    Análisis Ejecutivo
                </button>
                <button
                    onClick={() => setActiveTab('actuarial')}
                    style={{
                        ...tabStyle(activeTab === 'actuarial'),
                        padding: '10px 25px',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                        borderRadius: '8px 8px 0 0',
                        transition: 'all 0.3s ease',
                        backgroundColor: activeTab === 'actuarial' ? '#3498db' : 'transparent',
                        color: activeTab === 'actuarial' ? 'white' : '#7f8c8d',
                        border: '1px solid #ddd',
                        borderBottom: activeTab === 'actuarial' ? '2px solid #3498db' : '1px solid #ddd',
                        boxShadow: activeTab === 'actuarial' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
                    }}
                >
                    Calculadora Actuarial
                </button>
                <button
                    onClick={() => {
                        setActiveTab('validation');
                        fetchValidation();
                    }}
                    style={{
                        ...tabStyle(activeTab === 'validation'),
                        padding: '10px 25px',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                        borderRadius: '8px 8px 0 0',
                        transition: 'all 0.3s ease',
                        backgroundColor: activeTab === 'validation' ? '#3498db' : 'transparent',
                        color: activeTab === 'validation' ? 'white' : '#7f8c8d',
                        border: '1px solid #ddd',
                        borderBottom: activeTab === 'validation' ? '2px solid #3498db' : '1px solid #ddd',
                        boxShadow: activeTab === 'validation' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
                    }}
                >
                    Validación Estadística
                </button>
                <button
                    onClick={() => {
                        setActiveTab('renewal');
                        fetchRenewal();
                    }}
                    style={{
                        ...tabStyle(activeTab === 'renewal'),
                        padding: '10px 25px',
                        cursor: 'pointer',
                        fontWeight: 'bold',
                        borderRadius: '8px 8px 0 0',
                        transition: 'all 0.3s ease',
                        backgroundColor: activeTab === 'renewal' ? '#3498db' : 'transparent',
                        color: activeTab === 'renewal' ? 'white' : '#7f8c8d',
                        border: '1px solid #ddd',
                        borderBottom: activeTab === 'renewal' ? '2px solid #3498db' : '1px solid #ddd',
                        boxShadow: activeTab === 'renewal' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
                    }}
                >
                    Renovación de Contrato
                </button>
                {auth.role === 'admin' && (
                    <button
                        onClick={() => setActiveTab('admin')}
                        style={{
                            ...tabStyle(activeTab === 'admin'),
                            padding: '10px 25px',
                            cursor: 'pointer',
                            fontWeight: 'bold',
                            borderRadius: '8px 8px 0 0',
                            transition: 'all 0.3s ease',
                            backgroundColor: activeTab === 'admin' ? '#e74c3c' : 'transparent',
                            color: activeTab === 'admin' ? 'white' : '#7f8c8d',
                            border: '1px solid #ddd',
                            borderBottom: activeTab === 'admin' ? '2px solid #e74c3c' : '1px solid #ddd',
                            boxShadow: activeTab === 'admin' ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
                        }}
                    >
                        Administración
                    </button>
                )}
            </div>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '20px', marginBottom: '40px', justifyContent: 'center', alignItems: 'center', backgroundColor: 'white', padding: '20px', borderRadius: '12px', boxShadow: '0 4px 6px rgba(0,0,0,0.05)' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', alignItems: 'center' }}>
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                        <input
                            type="file"
                            ref={fileInputRef}
                            onChange={(e) => setFile(e.target.files[0])}
                            style={{ display: 'none' }}
                        />
                        <button
                            onClick={() => fileInputRef.current.click()}
                            style={{...btnStyle, backgroundColor: '#95a5a6'}}
                        >
                            Seleccionar Archivo
                        </button>
                        <button
                            onClick={handleUpload}
                            disabled={loading || uploadStatus === 'uploading' || !file}
                            style={{
                                ...btnStyle,
                                backgroundColor: uploadStatus === 'success' ? '#2ecc71' : (uploadStatus === 'error' ? '#e74c3c' : '#3498db')
                            }}
                        >
                            {uploadStatus === 'uploading' ? 'Procesando...' : (uploadStatus === 'success' ? '¡Cargado!' : 'Cargar y Analizar')}
                        </button>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '5px' }}>
                        {file && (
                            <span style={{ fontSize: '12px', color: '#34495e', fontStyle: 'italic' }}>
                                Archivo seleccionado: <strong>{file.name}</strong>
                            </span>
                        )}
                        {uploadMessage && (
                            <span style={{ fontSize: '12px', color: uploadStatus === 'success' ? '#27ae60' : '#c0392b', fontWeight: 'bold' }}>
                                {uploadMessage}
                            </span>
                        )}
                    </div>
                </div>

                <div style={{ borderLeft: '1px solid #ddd', paddingLeft: '20px', display: 'flex', gap: '10px', alignItems: 'center' }}>

                    <select
                        value={ramo}
                        onChange={(e) => setRamo(e.target.value)}
                        style={inputStyle}
                    >
                        <option value="">Todos los ramos</option>
                        {(queryRamos?.ramos || []).map(r => (
                            <option key={r} value={r}>{r}</option>
                        ))}
                    </select>
                    <button onClick={() => queryClient.invalidateQueries({ queryKey: ['analysis'] })} style={btnStyle}>Aplicar Filtro</button>
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
                    <button onClick={() => queryClient.invalidateQueries({ queryKey: ['projections'] })} disabled={loading} style={btnStyle}>Simular Escenario</button>
                </div>

                <div style={{ borderLeft: '1px solid #ddd', paddingLeft: '20px' }}>
                    <button onClick={handleViewTriangle} disabled={loading} style={btnStyle}>Ver Triángulo</button>
                </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                {renderContent()}
            </div>
        </div>
    );
}

const tabStyle = (isActive) => ({
    padding: '10px 25px',
    cursor: 'pointer',
    fontWeight: 'bold',
    borderRadius: '8px 8px 0 0',
    transition: 'all 0.3s ease',
    backgroundColor: isActive ? '#3498db' : 'transparent',
    color: isActive ? 'white' : '#7f8c8d',
    border: '1px solid #ddd',
    borderBottom: isActive ? '2px solid #3498db' : '1px solid #ddd',
    boxShadow: isActive ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
});

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
