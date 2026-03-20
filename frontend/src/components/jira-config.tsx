import React from 'react';
import { RefreshCw } from 'lucide-react';

export interface JiraConfigProps {
  loading: boolean;
  connectionError?: string;
  handleConnectJira: () => void;
  apiKey?: string;
}

const JiraConfig: React.FC<JiraConfigProps> = ({ loading, connectionError, handleConnectJira, apiKey }) => {
  return (
    <section style={{ maxWidth: '500px', margin: '4rem auto', backgroundColor: '#fff', padding: '2rem', borderRadius: '8px', border: '1px solid #eee', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', textAlign: 'center' }}>
      <h2 style={{ marginTop: 0 }}>Jira Connection & API</h2>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        Configure your Jira connection and access your programmatic API key.
      </p>
      
      {connectionError && <div style={{ color: 'red', marginBottom: '1.5rem', textAlign: 'left' }}>{connectionError}</div>}
      
      <div style={{ marginBottom: '2.5rem' }}>
        <h3 style={{ fontSize: '1rem', color: '#333', textAlign: 'left', marginBottom: '1rem' }}>Atlassian OAuth</h3>
        <button
          onClick={handleConnectJira}
          disabled={loading}
          style={{ 
            width: '100%', 
            padding: '1rem', 
            backgroundColor: loading ? '#ccc' : '#0052cc', 
            color: '#fff', 
            border: 'none', 
            borderRadius: '4px', 
            cursor: loading ? 'not-allowed' : 'pointer',
            fontSize: '1.1rem',
            fontWeight: 'bold',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: '0.75rem'
          }}
        >
          <RefreshCw size={20} className={loading ? 'animate-spin' : ''} />
          {loading ? 'Redirecting to Atlassian...' : 'Connect with Atlassian'}
        </button>
        <p style={{ fontSize: '0.85rem', color: '#888', marginTop: '0.75rem', textAlign: 'left' }}>
          Redirects to Atlassian to authorize this application.
        </p>
      </div>

      {apiKey && (
        <div style={{ borderTop: '1px solid #eee', paddingTop: '1.5rem', textAlign: 'left' }}>
          <h3 style={{ fontSize: '1rem', color: '#333', marginBottom: '0.5rem' }}>Your API Key</h3>
          <p style={{ fontSize: '0.85rem', color: '#666', marginBottom: '1rem' }}>
            Use this key in the <code>X-API-Key</code> header for programmatic access to report findings.
          </p>
          <div style={{ 
            padding: '0.75rem', 
            backgroundColor: '#f4f5f7', 
            borderRadius: '4px', 
            fontFamily: 'monospace', 
            wordBreak: 'break-all',
            border: '1px solid #dfe1e6',
            color: '#172b4d'
          }}>
            {apiKey}
          </div>
        </div>
      )}
    </section>
  );
};

export default JiraConfig;
