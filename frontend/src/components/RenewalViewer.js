import React, { useState } from 'react';
import { api } from '../services/api';

const RenewalViewer = ({ data, token, ramo, onActivate }) => {
    if (!data) return <div style={{ textAlign: 'center', padding: '40px', color: '#7f8c8d' }}>No hay datos de renovación disponibles.</div>;

    const { current_contract, suggested_contract, analysis, premium_adjustment } = data;

    const handleActivate = async () => {
        try {
            await api.activateContract({
                ramo,
                contract_type: suggested_contract.type,
                priority: suggested_contract.priority,
                limit: suggested_contract.limit,
                cession_pct: suggested_contract.cession_pct,
                token
            });
            alert('Contrato activado exitosamente');
            onActivate();
        } catch (error) {
            alert('Error al activar el contrato');
        }
    };

    return (
        <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            maxWidth: '1000px',
            margin: '0 auto'
        }}>
            <h2 style={{ color: '#2c3e50', textAlign: 'center', marginBottom: '30px' }}>Propuesta de Renovación de Contrato</h2>

            {/* Alert Section */}
            {analysis.solvency_alert === "Sugerir Cesión Urgente" && (
                <div style={{
                    backgroundColor: '#ffeaea',
                    borderLeft: '5px solid #e74c3c',
                    padding: '15px',
                    marginBottom: '20px',
                    borderRadius: '4px',
                    color: '#c0392b',
                    fontWeight: 'bold'
                }}>
                    ⚠️ ALERTA DE SOLVENCIA: El IBNR proyectado supera el 30% del capital disponible. Se recomienda aumentar la cesión al reasegurador.
                </div>
            )}

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '30px' }}>
                {/* Current Contract */}
                <div style={{ padding: '20px', backgroundColor: '#f8f9fa', borderRadius: '8px', border: '1px solid #ddd' }}>
                    <h3 style={{ color: '#7f8c8d', fontSize: '16px', borderBottom: '1px solid #ddd', paddingBottom: '10px' }}>Contrato Actual</h3>
                    <div style={{ marginTop: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <p><strong style={{color: '#2c3e50'}}>Tipo:</strong> {current_contract?.type || 'N/A'}</p>
                        <p><strong style={{color: '#2c3e50'}}>Prioridad/Retención:</strong> ${current_contract?.priority?.toLocaleString() || 0}</p>
                        <p><strong style={{color: '#2c3e50'}}>Límite:</strong> ${current_contract?.limit?.toLocaleString() || 0}</p>
                        <p><strong style={{color: '#2c3e50'}}>Cesión:</strong> {current_contract?.cession_pct || 0}%</p>
                    </div>
                </div>

                {/* Suggested Contract */}
                <div style={{ padding: '20px', backgroundColor: '#eefafb', borderRadius: '8px', border: '1px solid #3498db' }}>
                    <h3 style={{ color: '#3498db', fontSize: '16px', borderBottom: '1px solid #3498db', paddingBottom: '10px' }}>Sugerencia de Renovación</h3>
                    <div style={{ marginTop: '15px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
                        <p><strong style={{color: '#2c3e50'}}>Tipo:</strong> {suggested_contract.type}</p>
                        <p><strong style={{color: '#2c3e50'}}>Prioridad/Retención:</strong> ${suggested_contract.priority.toLocaleString()}</p>
                        <p><strong style={{color: '#2c3e50'}}>Límite:</strong> ${suggested_contract.limit.toLocaleString()}</p>
                        <p><strong style={{color: '#2c3e50'}}>Cesión:</strong> {suggested_contract.cession_pct.toFixed(2)}%</p>
                    </div>
                </div>
            </div>

            {/* Technical Justification */}
            <div style={{ marginTop: '30px', padding: '20px', backgroundColor: '#fdfdfd', borderRadius: '8px', border: '1px solid #eee' }}>
                <h3 style={{ color: '#2c3e50', fontSize: '16px', marginBottom: '10px' }}>Justificación Técnica</h3>
                <ul style={{ fontSize: '14px', color: '#7f8c8d', lineHeight: '1.6' }}>
                    {analysis.suggestions.map((s, i) => <li key={i}>{s}</li>)}
                    <li><strong style={{color: '#2c3e50'}}>Tendencia:</strong> {analysis.trend}</li>
                    <li><strong style={{color: '#2c3e50'}}>Ajuste de Prima:</strong> {premium_adjustment}</li>
                </ul>
            </div>

            <div style={{ marginTop: '30px', textAlign: 'center' }}>
                <button
                    onClick={handleActivate}
                    style={{
                        padding: '12px 30px',
                        backgroundColor: '#2ecc71',
                        color: 'white',
                        border: 'none',
                        borderRadius: '6px',
                        fontWeight: 'bold',
                        cursor: 'pointer',
                        fontSize: '16px'
                    }}
                >
                    Aceptar y Activar Contrato
                </button>
            </div>
        </div>
    );
};

export default RenewalViewer;
