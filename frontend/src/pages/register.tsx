/**
 * Register Page Component.
 * Provides a form for new users to create an account.
 */

import React, { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { authApi } from '../api';

const Register: React.FC = () => {
  // State for form inputs
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  
  // UI feedback states
  const [error, setError] = useState<string | undefined>(undefined);
  const [loading, setLoading] = useState(false);
  
  const navigate = useNavigate();

  /**
   * Handles the registration form submission.
   */
  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(undefined);
    try {
      const { access_token } = await authApi.register(username, email, password);
      // Store the JWT token for use in subsequent authenticated requests
      localStorage.setItem('token', access_token);
      navigate('/dashboard');
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to register. Username might already exist.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100vh', backgroundColor: '#f5f5f5' }}>
      <form onSubmit={handleRegister} style={{ padding: '2rem', backgroundColor: '#fff', borderRadius: '8px', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', width: '320px' }}>
        <h2 style={{ color: '#333', marginTop: 0 }}>Create Account</h2>
        
        {error && <div style={{ color: 'red', marginBottom: '1rem', fontSize: '0.9rem' }}>{error}</div>}
        
        <div style={{ marginBottom: '1rem', textAlign: 'left' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: '#666' }}>Username</label>
          <input
            type="text"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc', boxSizing: 'border-box' }}
            required
          />
        </div>

        <div style={{ marginBottom: '1rem', textAlign: 'left' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: '#666' }}>Email</label>
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc', boxSizing: 'border-box' }}
            required
          />
        </div>
        
        <div style={{ marginBottom: '1.5rem', textAlign: 'left' }}>
          <label style={{ display: 'block', marginBottom: '0.5rem', color: '#666' }}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc', boxSizing: 'border-box' }}
            required
          />
        </div>
        
        <button
          type="submit"
          disabled={loading}
          style={{ 
            width: '100%', 
            padding: '0.75rem', 
            backgroundColor: '#0052cc', 
            color: '#fff', 
            border: 'none', 
            borderRadius: '4px', 
            cursor: loading ? 'not-allowed' : 'pointer',
            fontWeight: 'bold'
          }}
        >
          {loading ? 'Creating account...' : 'Sign Up'}
        </button>

        <div style={{ marginTop: '1.5rem', textAlign: 'center', fontSize: '0.9rem' }}>
          <span style={{ color: '#666' }}>Already have an account?</span>
          {' '}
          <Link to="/login" style={{ color: '#0052cc', textDecoration: 'underline' }}>Login</Link>
        </div>
      </form>
    </div>
  );
};

export default Register;
