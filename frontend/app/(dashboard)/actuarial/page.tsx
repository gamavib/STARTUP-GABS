'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../../../src/services/api';
import TriangleViewer from '../../../src/components/TriangleViewer';

export default function ActuarialPage() {
    const queryClient = useQueryClient();
    const [selectedRamo, setSelectedRamo] = useState('');
    const [selectedMetric, setSelectedMetric] = useState('paid');
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

    // Hook para obtener los ramos disponibles
    const { data: ramos, isLoading: loadingRamos } = useQuery({
        queryKey: ['ramos'],
        queryFn: () => api.getRamos(token),
        enabled: !!token,
    });

    // Hook para obtener los datos del triángulo
    const { data: triangleData, isLoading: loadingTriangle } = useQuery({
        queryKey: ['triangle', selectedRamo, selectedMetric],
        queryFn: () => api.getTriangleData({ ramo: selectedRamo, metric: selectedMetric, token }),
        enabled: !!selectedRamo && !!token,
    });

    const handleRamoChange = (newRamo) => {
        setSelectedRamo(newRamo);
    };

    const handleMetricChange = (newMetric) => {
        setSelectedMetric(newMetric);
    };

    if (!token) {
        return <div style={{ textAlign: 'center', padding: '40px', color: '#e74c3c' }}>Sesión no autenticada. Por favor, inicie sesión.</div>;
    }

    return (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            <div style={{
                backgroundColor: 'white',
                padding: '20px',
                borderRadius: '12px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.05)',
                display: 'flex',
                gap: '20px',
                alignItems: 'center'
            }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Seleccionar Ramo</label>
                    <select
                        value={selectedRamo}
                        onChange={(e) => handleRamoChange(e.target.value)}
                        style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd', minWidth: '200px' }}
                    >
                        <option value="">Seleccione un ramo...</option>
                        {ramos?.map((r: any) => (
                            <option key={r} value={r}>{r}</option>
                        ))}
                    </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Métrica de Análisis</label>
                    <select
                        value={selectedMetric}
                        onChange={(e) => handleMetricChange(e.target.value)}
                        style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                    >
                        <option value="paid">Siniestros Pagados</option>
                        <option value="reserve">Reservas Técnicas</option>
                        <option value="total">Total (Pagados + Reservas)</option>
                    </select>
                </div>
            </div>

            {loadingRamos || loadingTriangle ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#3498db' }}>
                    Sincronizando datos con el motor actuarial...
                </div>
            ) : (
                <TriangleViewer
                    initialTriangleData={triangleData}
                    initialRamo={selectedRamo}
                    token={token}
                    onRamoChange={handleRamoChange}
                />
            )}
        </div>
    );
}