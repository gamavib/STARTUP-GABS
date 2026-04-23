import React, { useState } from 'react';
import { api } from '../services/api';

const TriangleViewer = ({ initialTriangleData, initialRamo, token, onClose }) => {
    const [triangleData, setTriangleData] = useState(initialTriangleData);
    const [ramo, setRamo] = useState(initialRamo || '');
    const [metric, setMetric] = useState(initialTriangleData?.metric || 'paid');
    const [loading, setLoading] = useState(false);

    const fetchTriangle = async (selectedRamo, selectedMetric) => {
        if (!token) {
            console.error("Auth token is missing in TriangleViewer");
            alert('Error: Sesión no autenticada');
            return;
        }
        setLoading(true);
        try {
            const data = await api.getTriangleData({
                ramo: selectedRamo,
                metric: selectedMetric,
                token: token
            });
            setTriangleData(data);
        } catch (error) {
            alert('Error al actualizar los datos del triángulo');
        } finally {
            setLoading(false);
        }
    };

    const handleRamoChange = (e) => {
        const newRamo = e.target.value;
        setRamo(newRamo);
        fetchTriangle(newRamo, metric);
    };

    const handleMetricChange = (e) => {
        const newMetric = e.target.value;
        setMetric(newMetric);
        fetchTriangle(ramo, newMetric);
    };

    if (!triangleData) return null;

    const { ramo: currentRamo, triangle_data, triangle_shape, metric: currentMetric } = triangleData;
    const years = Object.keys(triangle_data);
    const devYears = years.length > 0 ? Object.keys(triangle_data[years[0]]) : [];

    const metricLabels = {
        paid: 'Pagados',
        reserve: 'Reservas',
        total: 'Total (Pagado + Reserva)'
    };

    // Calcular totales por fila (Suma de desarrollo por año de origen)
    const rowTotals = {};
    years.forEach(year => {
        rowTotals[year] = Object.values(triangle_data[year]).reduce((a, b) => a + b, 0);
    });

    // Calcular totales por columna (Suma de todos los años de origen para ese año de desarrollo)
    const colTotals = {};
    devYears.forEach(devYear => {
        colTotals[devYear] = years.reduce((sum, year) => sum + triangle_data[year][devYear], 0);
    });

    const grandTotal = Object.values(rowTotals).reduce((a, b) => a + b, 0);

    return (
        <div style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0,0,0,0.5)',
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            zIndex: 1000
        }}>
            <div style={{
                backgroundColor: 'white',
                padding: '30px',
                borderRadius: '8px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.3)',
                maxWidth: '98vw',
                maxHeight: '90vh',
                overflow: 'auto'
            }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
                    <h2 style={{ margin: 0, color: '#2c3e50' }}>Análisis de Triángulos Actuariales</h2>
                    <button
                        onClick={onClose}
                        style={{
                            background: '#e74c3c',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            padding: '8px 16px',
                            cursor: 'pointer',
                            fontWeight: 'bold'
                        }}
                    >
                        Cerrar
                    </button>
                </div>

                <div style={{
                    display: 'flex',
                    gap: '20px',
                    marginBottom: '20px',
                    padding: '15px',
                    backgroundColor: '#f8f9fa',
                    borderRadius: '8px',
                    border: '1px solid #ddd',
                    alignItems: 'center'
                }}>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                        <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Ramo</label>
                        <input
                            type="text"
                            value={ramo}
                            onChange={handleRamoChange}
                            placeholder="Ej: Autos, Vida..."
                            style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc' }}
                        />
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '5px' }}>
                        <label style={{ fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d' }}>Métrica</label>
                        <select
                            value={metric}
                            onChange={handleMetricChange}
                            style={{ padding: '6px', borderRadius: '4px', border: '1px solid #ccc' }}
                        >
                            <option value="paid">Pagados</option>
                            <option value="reserve">Reservas</option>
                            <option value="total">Total</option>
                        </select>
                    </div>
                    {loading && <div style={{ color: '#3498db', fontSize: '14px', fontWeight: 'bold' }}>Cargando...</div>}
                </div>

                <div style={{ marginBottom: '20px' }}>
                    <p style={{ color: '#2c3e50', fontSize: '16px' }}>
                        <strong>Visualizando:</strong> {metricLabels[currentMetric]} | <strong>Ramo:</strong> {currentRamo || 'Global'}
                    </p>
                    <p style={{ fontSize: '14px', color: '#7f8c8d' }}>
                        Dimensiones: {triangle_shape.rows} años de origen × {triangle_shape.columns} años de desarrollo
                    </p>
                </div>

                <div style={{ overflowX: 'auto' }}>
                    <table style={{
                        borderCollapse: 'collapse',
                        width: '100%',
                        fontSize: '13px',
                        border: '1px solid #ddd'
                    }}>
                        <thead style={{ backgroundColor: '#f8f9fa' }}>
                            <tr style={{ backgroundColor: '#f1f3f5' }}>
                                <th style={{ border: '1px solid #ddd', padding: '8px', fontWeight: 'bold', textAlign: 'left' }}>Año Origen</th>
                                {devYears.map(devYear => (
                                    <th key={devYear} style={{ border: '1px solid #ddd', padding: '8px', fontWeight: 'bold' }}>
                                        Año {devYear}
                                    </th>
                                ))}
                                <th style={{ border: '1px solid #ddd', padding: '8px', fontWeight: 'bold', backgroundColor: '#e9ecef', color: '#2c3e50' }}>Total Fila</th>
                            </tr>
                        </thead>
                        <tbody>
                            {years.map(year => (
                                <tr key={year}>
                                    <td style={{ border: '1px solid #ddd', padding: '8px', fontWeight: 'bold', backgroundColor: '#fbfbfb', textAlign: 'left' }}>{year}</td>
                                    {devYears.map(devYear => (
                                        <td
                                            key={`${year}-${devYear}`}
                                            style={{
                                                border: '1px solid #ddd',
                                                padding: '8px',
                                                textAlign: 'right',
                                                backgroundColor: triangle_data[year][devYear] === 0 ? '#ffeaea' : 'white'
                                            }}
                                        >
                                            {triangle_data[year][devYear].toLocaleString(undefined, {
                                                minimumFractionDigits: 2,
                                                maximumFractionDigits: 2
                                            })}
                                        </td>
                                    ))}
                                    <td style={{
                                        border: '1px solid #ddd',
                                        padding: '8px',
                                        textAlign: 'right',
                                        fontWeight: 'bold',
                                        backgroundColor: '#f1f3f5',
                                        color: '#2c3e50'
                                    }}>
                                        {rowTotals[year].toLocaleString(undefined, {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2
                                        })}
                                    </td>
                                </tr>
                            ))}
                            <tr style={{ backgroundColor: '#f1f3f5', fontWeight: 'bold' }}>
                                <td style={{ border: '1px solid #ddd', padding: '8px', textAlign: 'left', color: '#2c3e50' }}>Total Columna</td>
                                {devYears.map(devYear => (
                                    <td key={`total-${devYear}`} style={{
                                        border: '1px solid #ddd',
                                        padding: '8px',
                                        textAlign: 'right',
                                        color: '#2c3e50'
                                    }}>
                                        {colTotals[devYear].toLocaleString(undefined, {
                                            minimumFractionDigits: 2,
                                            maximumFractionDigits: 2
                                        })}
                                    </td>
                                ))}
                                <td style={{
                                    border: '1px solid #ddd',
                                    padding: '8px',
                                    textAlign: 'right',
                                    backgroundColor: '#d1d8e0',
                                    color: '#2c3e50',
                                    fontSize: '14px'
                                }}>
                                    {grandTotal.toLocaleString(undefined, {
                                        minimumFractionDigits: 2,
                                        maximumFractionDigits: 2
                                    })}
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div style={{ marginTop: '20px', fontSize: '12px', color: '#7f8c8d' }}>
                    <p><strong style={{ color: '#e74c3c' }}>Nota:</strong> Las celdas en rojo indican períodos sin datos (valor 0).</p>
                </div>
            </div>
        </div>
    );
};

export default TriangleViewer;