'use client';

import React, { useState } from 'react';
import { api } from '../../../src/services/api';
import { useRouter } from 'next/navigation';

// Helper simple para manejar cookies en el cliente
const setCookie = (name: string, value: string, days = 7) => {
    const date = new Date();
    date.setTime(date.getTime() + (days * 24 * 60 * 60 * 1000));
    const expires = "expires=" + date.toUTCString();
    document.cookie = `${name}=${value};${expires};path=/;SameSite=Lax`;
};

export default function LoginPage() {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState('');
    const router = useRouter();

    const handleSubmit = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError('');

        try {
            const data = await api.login(email, password);

            // 1. Persistencia en localStorage (para compatibilidad con componentes actuales)
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('company_id', data.company_id || 'default');

            // 2. Persistencia en Cookies (CRÍTICO para el Middleware de Next.js)
            setCookie('token', data.access_token);

            // Redirigir al dashboard
            router.push('/dashboard');
        } catch (err) {
            setError('Credenciales incorrectas o error de conexión con el servidor');
            console.error("Login error:", err);
        } finally {
            setLoading(false);
        }
    };

    return (
        <div style={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            minHeight: '100vh',
            backgroundColor: '#f4f7f6',
            fontFamily: 'sans-serif'
        }}>
            <div style={{
                backgroundColor: 'white',
                padding: '40px',
                borderRadius: '16px',
                boxShadow: '0 10px 25px rgba(0,0,0,0.1)',
                width: '100%',
                maxWidth: '400px'
            }}>
                <div style={{ textAlign: 'center', marginBottom: '30px' }}>
                    <h2 style={{ color: '#2c3e50', margin: '0 0 10px 0' }}>Acceso Actuarial</h2>
                    <p style={{ color: '#7f8c8d', fontSize: '14px' }}>SaaS de Optimización de Reaseguro</p>
                </div>

                <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
                    <div>
                        <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d', marginBottom: '5px' }}>CORREO ELECTRÓNICO</label>
                        <input
                            type="email"
                            value={email}
                            onChange={(e) => setEmail(e.target.value)}
                            placeholder="usuario@empresa.com"
                            required
                            style={{
                                width: '100%',
                                padding: '12px',
                                borderRadius: '6px',
                                border: '1px solid #ddd',
                                boxSizing: 'border-box',
                                fontSize: '16px'
                            }}
                        />
                    </div>

                    <div>
                        <label style={{ display: 'block', fontSize: '12px', fontWeight: 'bold', color: '#7f8c8d', marginBottom: '5px' }}>CONTRASEÑA</label>
                        <input
                            type="password"
                            value={password}
                            onChange={(e) => setPassword(e.target.value)}
                            placeholder='••••••••'
                            required
                            style={{
                                width: '100%',
                                padding: '12px',
                                borderRadius: '6px',
                                border: '1px solid #ddd',
                                boxSizing: 'border-box',
                                fontSize: '16px'
                            }}
                        />
                    </div>

                    {error && (
                        <div style={{ color: '#e74c3c', fontSize: '14px', textAlign: 'center', backgroundColor: '#fdecea', padding: '10px', borderRadius: '4px' }}>
                            {error}
                        </div>
                    )}

                    <button
                        type="submit"
                        disabled={loading}
                        style={{
                            padding: '12px',
                            backgroundColor: '#3498db',
                            color: 'white',
                            border: 'none',
                            borderRadius: '6px',
                            cursor: 'pointer',
                            fontWeight: 'bold',
                            fontSize: '16px',
                            transition: 'background 0.2s',
                            opacity: loading ? 0.7 : 1
                        }}
                    >
                        {loading ? 'Autenticando...' : 'Ingresar al Sistema'}
                    </button>
                </form>
            </div>
        </div>
    );
}