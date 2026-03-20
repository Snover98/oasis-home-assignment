/**
 * Root Application Component.
 * Sets up the routing structure and protected route logic for the application.
 */

import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { authApi } from './api';
import Login from './pages/login';
import Register from './pages/register';
import Dashboard from './pages/dashboard';

/**
 * A wrapper component that checks whether the browser session is authenticated.
 */
const ProtectedRoute = ({ children }: { children: React.ReactNode }) => {
  const [status, setStatus] = useState<'loading' | 'authenticated' | 'unauthenticated'>('loading');

  useEffect(() => {
    let active = true;

    const verifySession = async () => {
      try {
        await authApi.getCurrentUser();
        if (active) {
          setStatus('authenticated');
        }
      } catch {
        if (active) {
          setStatus('unauthenticated');
        }
      }
    };

    verifySession();
    return () => {
      active = false;
    };
  }, []);

  if (status === 'loading') {
    return <div style={{ padding: '4rem', textAlign: 'center' }}>Loading session...</div>;
  }

  if (status === 'unauthenticated') {
    return <Navigate to="/login" replace />;
  }
  return <>{children}</>;
};

function App() {
  return (
    <Router>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        
        {/* Private Routes */}
        <Route
          path="/dashboard"
          element={
            <ProtectedRoute>
              <Dashboard />
            </ProtectedRoute>
          }
        />
        
        {/* Default redirect to Dashboard (which will trigger ProtectedRoute check) */}
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </Router>
  );
}

export default App;
