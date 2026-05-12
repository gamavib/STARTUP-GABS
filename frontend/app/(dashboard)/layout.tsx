'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();

  const menuItems = [
    { name: 'Dashboard', path: '/dashboard', icon: '📊' },
    { name: 'Calculadora Actuarial', path: '/actuarial', icon: '📐' },
    { name: 'Backtesting', path: '/backtesting', icon: '📉' },
    { name: 'Configuración', path: '/settings', icon: '⚙️' },
  ];

  return (
    <div style={{ display: 'flex', minHeight: '100vh', backgroundColor: '#f4f7f6' }}>
      {/* Sidebar */}
      <aside style={{
        width: '260px',
        backgroundColor: '#2c3e50',
        color: 'white',
        display: 'flex',
        flexDirection: 'column',
        padding: '20px 0',
        position: 'fixed',
        height: '100vh'
      }}>
        <div style={{ padding: '0 20px 30px', textAlign: 'center' }}>
          <h2 style={{ fontSize: '20px', fontWeight: 'bold', color: '#ecf0f1' }}>SaaS Actuarial</h2>
          <div style={{ fontSize: '12px', color: '#bdc3c7' }}>Optimization Platform</div>
        </div>

        <nav style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '5px' }}>
          {menuItems.map((item) => (
            <Link
              key={item.path}
              href={item.path}
              style={{
                padding: '12px 20px',
                textDecoration: 'none',
                color: pathname === item.path ? '#fff' : '#bdc3c7',
                backgroundColor: pathname === item.path ? '#34495e' : 'transparent',
                fontWeight: pathname === item.path ? 'bold' : 'normal',
                transition: 'all 0.2s',
                display: 'flex',
                alignItems: 'center',
                gap: '12px'
              }}
            >
              <span>{item.icon}</span>
              {item.name}
            </Link>
          ))}
        </nav>

        <div style={{ padding: '20px', borderTop: '1px solid #3e4f5f' }}>
          <button
            onClick={() => {
              localStorage.clear();
              window.location.href = '/';
            }}
            style={{
              width: '100%',
              padding: '10px',
              backgroundColor: 'transparent',
              color: '#e74c3c',
              border: '1px solid #e74c3c',
              borderRadius: '4px',
              cursor: 'pointer',
              fontWeight: 'bold'
            }}
          >
            Cerrar Sesión
          </button>
        </div>
      </aside>

      {/* Main Content */}
      <main style={{ marginLeft: '260px', flex: 1, padding: '40px' }}>
        <header style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '30px',
          paddingBottom: '20px',
          borderBottom: '1px solid #ddd'
        }}>
          <h1 style={{ color: '#2c3e50', margin: 0 }}>Panel de Control</h1>
          <div style={{ display: 'flex', alignItems: 'center', gap: '15px' }}>
            <span style={{ color: '#7f8c8d', fontSize: '14px' }}>Usuario Actuario</span>
            <div style={{ width: '35px', height: '35px', borderRadius: '50%', backgroundColor: '#3498db', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 'bold' }}>
              UA
            </div>
          </div>
        </header>
        {children}
      </main>
    </div>
  );
}