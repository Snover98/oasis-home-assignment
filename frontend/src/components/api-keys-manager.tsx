import React, { useState, useEffect } from 'react';
import { apiKeysApi } from '../api';
import type { APIKey } from '../models';
import { Trash2, Plus, Key } from 'lucide-react';

export const APIKeysManager: React.FC = () => {
  const [apiKeys, setApiKeys] = useState<APIKey[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | undefined>();
  
  const [newKeyName, setNewKeyName] = useState('');
  const [generatedKey, setGeneratedKey] = useState<string | null>(null);

  const fetchKeys = async () => {
    try {
      const keys = await apiKeysApi.list();
      setApiKeys(keys);
    } catch (err) {
      console.error('Failed to fetch API keys', err);
      setError('Failed to load API keys.');
    }
  };

  useEffect(() => {
    fetchKeys();
  }, []);

  const handleGenerate = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;
    
    setLoading(true);
    setError(undefined);
    setGeneratedKey(null);
    
    try {
      const newKey = await apiKeysApi.generate(newKeyName);
      setGeneratedKey(newKey.key); // Show the secret key once
      setNewKeyName('');
      await fetchKeys(); // Refresh list
    } catch (err) {
      setError('Failed to generate API key.');
    } finally {
      setLoading(false);
    }
  };

  const handleRevoke = async (id: string) => {
    if (!window.confirm('Are you sure you want to revoke this key? Any integrations using it will immediately fail.')) return;
    
    try {
      await apiKeysApi.revoke(id);
      await fetchKeys();
    } catch (err) {
      setError('Failed to revoke API key.');
    }
  };

  return (
    <section style={{ maxWidth: '600px', margin: '2rem auto', backgroundColor: '#fff', padding: '2rem', borderRadius: '8px', border: '1px solid #eee', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem' }}>
        <Key size={24} color="#0052cc" />
        <h2 style={{ margin: 0 }}>API Keys</h2>
      </div>
      
      <p style={{ color: '#666', marginBottom: '2rem', fontSize: '0.9rem' }}>
        Manage your API keys for programmatic access to the Oasis NHI system.
      </p>

      {error && <div style={{ color: 'red', marginBottom: '1rem', padding: '0.5rem', backgroundColor: '#fee' }}>{error}</div>}

      <div style={{ marginBottom: '2.5rem' }}>
        <h3 style={{ fontSize: '1rem', color: '#333', marginBottom: '1rem' }}>Generate New Key</h3>
        <form onSubmit={handleGenerate} style={{ display: 'flex', gap: '1rem' }}>
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key Name (e.g., CI/CD Pipeline)"
            style={{ flex: 1, padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
            required
          />
          <button
            type="submit"
            disabled={loading || !newKeyName.trim()}
            style={{
              padding: '0.5rem 1rem',
              backgroundColor: loading ? '#ccc' : '#0052cc',
              color: '#fff',
              border: 'none',
              borderRadius: '4px',
              cursor: loading ? 'not-allowed' : 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '0.5rem',
              fontWeight: 'bold'
            }}
          >
            <Plus size={18} /> {loading ? 'Generating...' : 'Generate'}
          </button>
        </form>
        
        {generatedKey && (
          <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#e3fcef', border: '1px solid #006644', borderRadius: '4px' }}>
            <strong style={{ color: '#006644', display: 'block', marginBottom: '0.5rem' }}>Success! Your new API key is:</strong>
            <code style={{ display: 'block', padding: '0.5rem', backgroundColor: '#fff', border: '1px solid #ccc', wordBreak: 'break-all' }}>
              {generatedKey}
            </code>
            <p style={{ color: '#666', fontSize: '0.8rem', marginTop: '0.5rem', marginBottom: 0 }}>
              Please copy this key now. You will not be able to see it again.
            </p>
          </div>
        )}
      </div>

      <div>
        <h3 style={{ fontSize: '1rem', color: '#333', marginBottom: '1rem' }}>Active Keys</h3>
        {apiKeys.length === 0 ? (
          <p style={{ color: '#888', fontStyle: 'italic' }}>No API keys found.</p>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #eee' }}>
                <th style={{ padding: '0.5rem 0', color: '#666' }}>Name</th>
                <th style={{ padding: '0.5rem 0', color: '#666' }}>Created</th>
                <th style={{ padding: '0.5rem 0', textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {apiKeys.map(key => (
                <tr key={key.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '0.75rem 0', fontWeight: 'bold' }}>{key.name}</td>
                  <td style={{ padding: '0.75rem 0', color: '#666', fontSize: '0.9rem' }}>
                    {new Date(key.created_at).toLocaleDateString()}
                  </td>
                  <td style={{ padding: '0.75rem 0', textAlign: 'right' }}>
                    <button
                      onClick={() => handleRevoke(key.id)}
                      style={{ background: 'none', border: 'none', color: '#de350b', cursor: 'pointer', display: 'inline-flex', alignItems: 'center', gap: '0.25rem', padding: '0.25rem' }}
                      title="Revoke Key"
                    >
                      <Trash2 size={16} /> <span style={{ fontSize: '0.8rem' }}>Revoke</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </section>
  );
};
