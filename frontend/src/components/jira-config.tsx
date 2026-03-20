import React from 'react';
import { RefreshCw } from 'lucide-react';

export interface JiraConfigProps {
  loading: boolean;
  connectionError?: string;
  handleConnectJira: () => void;
}

const JiraConfig: React.FC<JiraConfigProps> = ({ loading, connectionError, handleConnectJira }) => {
  return (
    <section style={{ maxWidth: '600px', margin: '0 auto 2rem', backgroundColor: '#fff', padding: '2rem', borderRadius: '8px', border: '1px solid #eee', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
      <h2 style={{ marginTop: 0 }}>Jira Connection</h2>
      <p style={{ color: '#666', marginBottom: '2rem' }}>
        Configure your Jira connection to enable issue reporting.
      </p>
      
      {connectionError && <div style={{ color: 'red', marginBottom: '1.5rem', textAlign: 'left' }}>{connectionError}</div>}
      
      <div>
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
    </section>
  );
};

export default JiraConfig;
