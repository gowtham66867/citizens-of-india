import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import CitizenSubmission from './pages/CitizenSubmission';
import MPDashboard from './pages/MPDashboard';

function Nav() {
  const { pathname } = useLocation();
  return (
    <nav style={{
      background: 'linear-gradient(135deg, #FF9933 0%, #FF7700 50%, #138808 100%)',
      padding: '0',
      boxShadow: '0 2px 8px rgba(0,0,0,0.15)'
    }}>
      <div className="container" style={{ display: 'flex', alignItems: 'center', gap: '2rem', height: '60px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span style={{ fontSize: '1.5rem' }}>🇮🇳</span>
          <span style={{ color: '#fff', fontWeight: 700, fontSize: '1.1rem', letterSpacing: '-0.3px' }}>
            Citizens of India
          </span>
        </div>
        <div style={{ display: 'flex', gap: '0.5rem', marginLeft: 'auto' }}>
          {[
            { to: '/', label: 'Submit Issue' },
            { to: '/dashboard', label: 'MP Dashboard' },
          ].map(({ to, label }) => (
            <Link key={to} to={to} style={{
              color: '#fff',
              textDecoration: 'none',
              padding: '6px 16px',
              borderRadius: '20px',
              fontSize: '0.9rem',
              fontWeight: 500,
              background: pathname === to ? 'rgba(255,255,255,0.25)' : 'transparent',
              transition: 'background 0.2s',
            }}>{label}</Link>
          ))}
        </div>
      </div>
    </nav>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Nav />
      <Routes>
        <Route path="/" element={<CitizenSubmission />} />
        <Route path="/dashboard" element={<MPDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}
