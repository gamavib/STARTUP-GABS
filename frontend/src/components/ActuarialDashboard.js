import React from 'react';
import ReactECharts from 'echarts-for-react';
import LdfTrendViewer from './LdfTrendViewer';

const ActuarialDashboard = ({ data, projectionData, contractDraft, onDownloadContract }) => {
    if (!data) return <div style={{textAlign: 'center', padding: '20px'}}>Cargue un archivo CSV para ver el análisis actuarial.</div>;

    const { ibnr, comparison, metrics, ramo } = data;

    const reserveOption = {
        title: { text: 'Comparativa de Reservas', left: 'center', textStyle: { fontSize: 16, color: '#2c3e50' } },
        tooltip: { trigger: 'axis', axisPointer: { type: 'shadow' } },
        grid: { left: '3%', right: '4%', bottom: '3%', containLabel: true },
        xAxis: {
            type: 'category',
            data: ['Contable', 'Técnica (Actuarial)'],
            axisLabel: { color: '#7f8c8d' }
        },
        yAxis: { type: 'value', axisLabel: { formatter: (value) => `$${value.toLocaleString()}` } },
        series: [
            {
                name: 'Monto de Reserva',
                type: 'bar',
                data: [comparison.reserva_contable, comparison.reserva_tecnica_actuarial],
                itemStyle: { color: '#3498db' },
                barWidth: '40%'
            }
        ]
    };

    return (
        <div style={{ padding: '20px', fontFamily: 'sans-serif' }}>
            <h2 style={{ color: '#2c3e50' }}>Análisis Actuarial: {ramo}</h2>

            <div style={{ display: 'flex', gap: '20px', marginBottom: '30px' }}>
                <div style={cardStyle}>
                    <h4 style={{margin: '0', color: '#7f8c8d'}}>IBNR Estimado</h4>
                    <p style={valueStyle}>${ibnr.ibnr_estimate.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
                </div>
                <div style={cardStyle}>
                    <h4 style={{margin: '0', color: '#7f8c8d'}}>Frecuencia</h4>
                    <p style={valueStyle}>{metrics.frecuencia.toFixed(4)}</p>
                </div>
                <div style={cardStyle}>
                    <h4 style={{margin: '0', color: '#7f8c8d'}}>Severidad Promedio</h4>
                    <p style={valueStyle}>${metrics.severidad.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
                </div>
                <div style={cardStyle}>
                    <h4 style={{margin: '0', color: '#7f8c8d'}}>Estado Reserva</h4>
                    <p style={{...valueStyle, color: comparison.status === 'Suficiente' ? '#27ae60' : '#e74c3c'}}>
                        {comparison.status}
                    </p>
                </div>
            </div>

            <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 2px 4px rgba(0,0,0,0.1)', marginBottom: '30px' }}>
                <div style={{ width: '100%', height: 350 }}>
                    <ReactECharts option={reserveOption} style={{ height: '100%', width: '100%' }} />
                </div>
            </div>

            <LdfTrendViewer ramo={ramo} />

            {projectionData && (
                <div style={{ backgroundColor: '#edf2f7', padding: '20px', borderRadius: '8px', borderLeft: '5px solid #3498db', marginBottom: '30px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                            <h3 style={{marginTop: 0}}>Proyección y Optimización de Reaseguro</h3>
                            <p><strong>IBNR Proyectado:</strong> ${projectionData.scenario.projected_ibnr.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
                            <p><strong>Sugerencia de Retención:</strong> ${projectionData.reinsurance_strategy.suggested_retention.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
                            <p><strong>Monto a Ceder:</strong> ${projectionData.reinsurance_strategy.ceded_amount.toLocaleString(undefined, {maximumFractionDigits: 0})}</p>
                        </div>
                        <div style={{ textAlign: 'right', maxWidth: '40%' }}>
                            <p style={{ fontWeight: 'bold', color: '#2c3e50' }}>{projectionData.reinsurance_strategy.recommendation}</p>
                            <p>Retención: {projectionData.reinsurance_strategy.retention_percentage.toFixed(2)}%</p>
                            <button
                                onClick={onDownloadContract}
                                style={{...btnStyle, backgroundColor: '#27ae60', marginTop: '10px'}}
                            >
                                Generar Borrador de Contrato
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {contractDraft && (
                <div style={{ backgroundColor: 'white', padding: '20px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', border: '1px solid #ddd' }}>
                    <h3 style={{color: '#2c3e50', borderBottom: '2px solid #3498db', paddingBottom: '10px'}}>Borrador de Contrato: {contractDraft.header.ramo}</h3>
                    <div style={{margin: '20px 0', fontSize: '14px', color: '#7f8c8d'}}>
                        Versión: {contractDraft.header.version} | Moneda: {contractDraft.header.currency}
                    </div>
                    <div style={{display: 'flex', gap: '40px', marginBottom: '20px'}}>
                        <div><strong>IBNR Base:</strong> ${contractDraft.technical_basis.projected_ibnr.toLocaleString()}</div>
                        <div><strong>Índice Volatilidad:</strong> {contractDraft.technical_basis.volatility_index.toFixed(2)}</div>
                    </div>
                    <div style={{display: 'flex', flexDirection: 'column', gap: '10px'}}>
                        {contractDraft.clauses.map((c, i) => (
                            <div key={i} style={{padding: '10px', backgroundColor: '#f9f9f9', borderRadius: '4px', borderLeft: '3px solid #3498db'}}>
                                <strong style={{display: 'block', color: '#2c3e50'}}>{c.clause}</strong>
                                <span style={{fontSize: '18px', fontWeight: 'bold', color: '#3498db'}}>{c.value}</span>
                                <p style={{margin: '5px 0 0 0', fontSize: '13px', color: '#7f8c8d'}}>{c.description}</p>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </div>
    );
};

const btnStyle = {
    padding: '8px 16px',
    color: 'white',
    border: 'none',
    borderRadius: '4px',
    cursor: 'pointer',
    fontWeight: 'bold'
};

const cardStyle = {
    backgroundColor: 'white',
    padding: '20px',
    borderRadius: '8px',
    boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
    flex: 1,
    textAlign: 'center'
};

const valueStyle = {
    fontSize: '24px',
    fontWeight: 'bold',
    margin: '10px 0 0 0'
};

export default ActuarialDashboard;
