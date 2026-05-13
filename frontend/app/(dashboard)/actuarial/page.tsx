'use client';

import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '@/services/api';
import TriangleViewer from '@/components/TriangleViewer';

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

    // Mutación para la carga de CSV
    const uploadMutation = useMutation({
        mutationFn: ({ file }) => {
            const formData = new FormData();
            formData.append('file', file);
            return api.uploadCsv(formData, token);
        },
        onSuccess: () => {
            // Refrescar ramos y datos del triángulo tras la carga
            queryClient.invalidateQueries({ queryKey: ['ramos'] });
            queryClient.invalidateQueries({ queryKey: ['triangle'] });
            alert('Archivo recibido. El motor actuarial está procesando los datos en segundo plano.');
        },
        onError: (error) => {
            console.error('Error uploading CSV:', error);
            alert('Error al subir el archivo. Verifique el formato del CSV.');
        }
    });

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            uploadMutation.mutate({ file });
        }
    };

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
                        {(ramos?.ramos || ramos)?.map((r: any) => (
                            <option key={r} value={r}>{r}</option>
                        ))}
                    </select>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '5px', marginLeft: 'auto' }}>
                    <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Carga de Datos</label>
                    <div style={{ position: 'relative', overflow: 'hidden', display: 'inline-block' }}>
                        <input
                            type="file"
                            accept=".csv"
                            onChange={handleFileUpload}
                            style={{
                                position: 'absolute',
                                left: 0,
                                top: 0,
                                opacity: 0,
                                width: '100%',
                                height: '100%',
                                cursor: 'pointer'
                            }}
                        />
                        <button
                            disabled={uploadMutation.isPending}
                            style={{
                                padding: '8px 16px',
                                borderRadius: '4px',
                                border: 'none',
                                backgroundColor: uploadMutation.isPending ? '#bdc3c7' : '#3498db',
                                color: 'white',
                                fontWeight: 'bold',
                                cursor: 'pointer',
                                whiteSpace: 'nowrap'
                            }}
                        >
                            {uploadMutation.isPending ? 'Subiendo...' : 'Cargar CSV'}
                        </button>
                    </div>
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