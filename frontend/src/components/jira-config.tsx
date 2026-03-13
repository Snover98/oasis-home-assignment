import React from 'react';
import { RefreshCw } from 'lucide-react';

export interface JiraConfigProps {
  loading: boolean;
  connectionError?: string;
  handleConnectJira: () => void;
}

const JiraConfig: React.FC<JiraConfigProps> = ({ loading, connectionError, handleConnectJira }) => {
  return (
    <section style={{ maxWidth: '500px', margin: '4rem auto', backgroundColor: '#fff', padding: '2rem', borderRadius: '8px', border: '1px solid #eee', boxShadow: '0 4px 6px rgba(0,0,0,0.1)', textAlign: 'center' }}>
      <h2 style={{ marginTop: 0 }}>Connect to Jira</h2>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        To report findings, you need to connect your Atlassian Jira account.
      </p>
      
      {connectionError && <div style={{ color: 'red', marginBottom: '1.5rem', textAlign: 'left' }}>{connectionError}</div>}
      
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
      
      <p style={{ fontSize: '0.85rem', color: '#888', marginTop: '1.5rem' }}>
        You will be redirected to Atlassian to authorize this application.
      </p>
    </section>
  );
};

export default JiraConfig;
