import React from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, BarChart, Bar } from 'recharts';

const BacktestingViewer = ({ data }) => {
    // Defensive check: Ensure data is an array and not empty
    if (!data || !Array.isArray(data) || data.length === 0) {
        return (
            <div style={{ textAlign: 'center', padding: '40px', color: '#7f8c8d', backgroundColor: 'white', borderRadius: '12px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}>
                <h3 style={{ color: '#2c3e50' }}>No hay datos de back-testing disponibles</h3>
                <p>Por favor, asegúrese de que haya suficientes años de historia en el ramo seleccionado para realizar una validación estadística.</p>
            </div>
        );
    }

    // Defensive Calculation of overall metrics
    let mae = 0;
    let avgRatio = 0;

    try {
        const validEntries = data.filter(entry =>
            entry && typeof entry.error === 'number' &&
            typeof entry.ratio === 'number'
        );

        if (validEntries.length > 0) {
            const totalError = validEntries.reduce((acc, curr) => acc + Math.abs(curr.error), 0);
            mae = totalError / validEntries.length;
            avgRatio = validEntries.reduce((acc, curr) => acc + curr.ratio, 0) / validEntries.length;
        }
    } catch (e) {
        console.error("Error calculating backtesting metrics:", e);
    }

    return (
        <div style={{
            backgroundColor: 'white',
            padding: '30px',
            borderRadius: '12px',
            boxShadow: '0 4px 12px rgba(0,0,0,0.1)',
            width: '100%',
            maxWidth: '1200px',
            margin: '0 auto',
            fontFamily: 'sans-serif'
        }}>
            <h2 style={{ color: '#2c3e50', marginBottom: '20px', textAlign: 'center' }}>Validación Estadística (Back-testing)</h2>

            <div style={{ display: 'flex', gap: '20px', marginBottom: '30px' }}>
                <div style={metricCardStyle}>
                    <h4 style={{ margin: '0', color: '#7f8c8d', fontSize: '14px' }}>MAE (Error Medio Absoluto)</h4>
                    <p style={metricValueStyle}>${mae.toLocaleString(undefined, { maximumFractionDigits: 2 })}</p>
                </div>
                <div style={metricCardStyle}>
                    <h4 style={{ margin: '0', color: '#7f8c8d', fontSize: '14px' }}>Ratio Promedio de Error</h4>
                    <p style={metricValueStyle}>{(avgRatio * 100).toFixed(2)}%</p>
                </div>
                <div style={metricCardStyle}>
                    <h4 style={{ margin: '0', color: '#7f8c8d', fontSize: '14px' }}>Años Analizados</h4>
                    <p style={metricValueStyle}>{data.length} años</p>
                </div>
            </div>

            <div style={{ marginBottom: '40px' }}>
                <h3 style={{ color: '#2c3e50', fontSize: '18px', marginBottom: '15px' }}>Análisis de Error por Año</h3>
                <div style={{ width: '100%', height: 400 }}>
                    <ResponsiveContainer>
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis dataKey="year" label={{ value: 'Año de Snapshot', position: 'insideBottom', offset: -5 }} />
                            <YAxis />
                            <Tooltip formatter={(value) => `$${value?.toLocaleString()}`} />
                            <Legend />
                            <Bar dataKey="error" fill="#e74c3c" name="Error de Predicción" />
                            <Bar dataKey="estimated" fill="#3498db" name="Reserva Estimada" />
                            <Bar dataKey="actual" fill="#2ecc71" name="Pago Real" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div style={{ overflowX: 'auto' }}>
                <table style={{
                    width: '100%',
                    borderCollapse: 'collapse',
                    fontSize: '14px',
                    textAlign: 'right'
                }}>
                    <thead style={{ backgroundColor: '#f8f9fa', color: '#2c3e50', fontWeight: 'bold' }}>
                        <tr style={{ backgroundColor: '#f8f9fa', color: '#2c3e50', fontWeight: 'bold' }}>
                            <th style={tableHeaderStyle}>Año</th>
                            <th style={tableHeaderStyle}>Estimado ($)</th>
                            <th style={tableHeaderStyle}>Real ($)</th>
                            <th style={tableHeaderStyle}>Error ($)</th>
                            <th style={tableHeaderStyle}>Ratio</th>
                        </tr>
                    </thead>
                    <tbody>
                        {data.map((row, i) => (
                            <tr key={i} style={{ borderBottom: '1px solid #eee' }}>
                                <td style={tableCellStyle}>{row.year || 'N/A'}</td>
                                <td style={tableCellStyle}>{(row.estimated || 0).toLocaleString()}</td>
                                <td style={tableCellStyle}>{(row.actual || 0).toLocaleString()}</td>
                                <td style={{...tableCellStyle, color: (row.error || 0) > 0 ? '#e74c3c' : '#27ae60'}}>
                                    {(row.error || 0).toLocaleString()}
                                </td>
                                <td style={tableCellStyle}>{( (row.ratio || 0) * 100).toFixed(2)}%</td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

const metricCardStyle = {
    flex: 1,
    padding: '20px',
    backgroundColor: '#f8f9fa',
    borderRadius: '8px',
    borderLeft: '4px solid #3498db',
    textAlign: 'center',
    boxShadow: '0 2px 4px rgba(0,0,0,0.05)'
};

const metricValueStyle = {
    fontSize: '24px',
    fontWeight: 'bold',
    margin: '10px 0 0 0',
    color: '#2c3e50'
};

const tableHeaderStyle = {
    padding: '12px',
    borderBottom: '2px solid #ddd',
    textAlign: 'right'
};

const tableCellStyle = {
    padding: '12px',
    borderBottom: '1px solid #eee'
};

export default BacktestingViewer;
