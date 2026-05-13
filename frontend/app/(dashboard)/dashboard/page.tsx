'use client';

import React, { useState, useEffect } from 'react';
import { api } from '@/services/api';
import ActuarialDashboard from '@/components/ActuarialDashboard';

export default function DashboardPage() {
    const [data, setData] = useState(null);
    const [projectionData, setProjectionData] = useState(null);
    const [contractDraft, setContractDraft] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const loadDashboardData = async () => {
            try {
                const token = localStorage.getItem('token');
                if (!token) {
                    setError('No se encontró token de sesión');
                    return;
                }

                // Carga paralela de datos para optimizar el tiempo de respuesta
                const [analysis, projections] = await Promise.all([
                    api.getActuarialAnalysis('', token),
                    api.getProjections({ ramo: '' }, token)
                ]);

                setData(analysis);
                setProjectionData(projections);
            } catch (err) {
                console.error("Error cargando dashboard:", err);
                setError('Error al conectar con el motor actuarial');
            } finally {
                setLoading(false);
            }
        };

        loadDashboardData();
    }, []);

    if (loading) return <div style={{ textAlign: 'center', padding: '40px', color: '#3498db' }}>Cargando análisis global...</div>;
    if (error) return <div style={{ textAlign: 'center', padding: '40px', color: '#e74c3c' }}>{error}</div>;

    return (
        <div>
            <div style={{ marginBottom: '20px', color: '#7f8c8d' }}>
                Bienvenido al Panel de Control. Aquí puede ver el estado general de sus reservas y la estrategia de optimización sugerida.
            </div>
            <ActuarialDashboard
                data={data}
                projectionData={projectionData}
                contractDraft={contractDraft}
                onDownloadContract={() => alert('Generando borrador de contrato...')}
            />
        </div>
    );
}