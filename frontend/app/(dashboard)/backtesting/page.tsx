'use client';

import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { api } from '../../../src/services/api';
import BacktestingViewer from '../../../src/components/BacktestingViewer';

export default function BacktestingPage() {
    const [selectedRamo, setSelectedRamo] = useState('');
    const [selectedMethod, setSelectedMethod] = useState('chain_ladder');
    const token = typeof window !== 'undefined' ? localStorage.getItem('token') : null;

    // Hook para obtener los ramos disponibles
    const { data: ramos, isLoading: loadingRamos } = useQuery({
        queryKey: ['ramos'],
        queryFn: () => api.getRamos(token),
        enabled: !!token,
    });

    // Hook para obtener los datos de backtesting
    const { data: backtestingData, isLoading: loadingData } = useQuery({
        queryKey: ['backtesting', selectedRamo, selectedMethod],
        queryFn: () => api.getBacktestingData({
            ramo: selectedRamo,
            method: selectedMethod,
            token
        }),
        enabled: !!selectedRamo && !!token,
    });

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
                    <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Ramo de Análisis</label>
                    <select
                        value={selectedRamo}
                        onChange={(e) => setSelectedRamo(e.target.value)}
                        style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd', minWidth: '200px' }}
                    >
                        <option value="">Seleccione un ramo...</option>
                        {ramos?.map((r: any) => (
                            <option key={r} value={r}>{r}</option>
                        ))}
                    </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Método de Proyección</label>
                    <select
                        value={selectedMethod}
                        onChange={(e) => setSelectedMethod(e.target.value)}
                        style={{ padding: '8px', borderRadius: '4px', border: '1px solid #ddd' }}
                    >
                        <option value="chain_ladder">Chain Ladder</option>
                        <option value="bf">Bornhuetter-Ferguson</option>
                        <option value="cape_cod">Cape Cod</option>
                    </select>
                </div>
            </div>

            {loadingRamos || loadingData ? (
                <div style={{ textAlign: 'center', padding: '40px', color: '#3498db' }}>
                    Ejecutando simulaciones de back-testing...
                </div>
            ) : (
                <BacktestingViewer data={backtestingData} />
            )}
        </div>
    );
}