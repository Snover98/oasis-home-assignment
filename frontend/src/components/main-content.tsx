import React from 'react';
import { RefreshCw, Send, ExternalLink } from 'lucide-react';
import type { Project, Ticket } from '../models';

export interface MainContentProps {
  projects: Project[];
  selectedProject: string;
  setSelectedProject: (key: string) => void;
  title: string;
  setTitle: (title: string) => void;
  description: string;
  setDescription: (desc: string) => void;
  loading: boolean;
  findingError?: string;
  recentTickets: Ticket[];
  handleCreateTicket: (e: React.FormEvent) => Promise<void>;
  handleTriggerBlogDigest: () => Promise<void>;
  fetchRecentTickets: () => Promise<void>;
}

const MainContent: React.FC<MainContentProps> = ({
  projects,
  selectedProject,
  setSelectedProject,
  title,
  setTitle,
  description,
  setDescription,
  loading,
  findingError,
  recentTickets,
  handleCreateTicket,
  handleTriggerBlogDigest,
  fetchRecentTickets,
}) => {
  return (
    <>
      <div style={{ marginBottom: '2rem', padding: '1rem 1.5rem', backgroundColor: '#fff', border: '1px solid #eee', borderRadius: '8px', display: 'flex', alignItems: 'center', gap: '1rem', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
        <label style={{ fontWeight: 'bold', margin: 0, whiteSpace: 'nowrap' }}>Active Jira Project:</label>
        <select
          value={selectedProject}
          onChange={(e) => setSelectedProject(e.target.value)}
          style={{ width: '100%', maxWidth: '400px', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc', backgroundColor: '#f9f9f9' }}
        >
          {projects.map((p) => (
            <option key={p.id} value={p.key}>{p.name} ({p.key})</option>
          ))}
        </select>
      </div>

      <main style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        {/* Left Column: Create Finding */}
        <section style={{ backgroundColor: '#fff', padding: '1.5rem', borderRadius: '8px', border: '1px solid #eee', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <h2 style={{ marginTop: 0 }}>Report NHI Finding</h2>
          <form onSubmit={handleCreateTicket}>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Title (Summary)</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="e.g., Stale Service Account: svc-deploy-prod"
                style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc' }}
                required
              />
            </div>
            <div style={{ marginBottom: '1rem' }}>
              <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 'bold' }}>Description</label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Provide detailed context regarding the identity finding..."
                rows={5}
                style={{ width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #ccc', resize: 'vertical' }}
                required
              />
            </div>
            {findingError && <div style={{ color: 'red', marginBottom: '1rem' }}>{findingError}</div>}
            <button
              type="submit"
              disabled={loading || !selectedProject || !title.trim()}
              style={{ 
                width: '100%', 
                padding: '0.75rem', 
                backgroundColor: (loading || !selectedProject || !title.trim()) ? '#ccc' : '#0052cc', 
                color: '#fff', 
                border: 'none', 
                borderRadius: '4px', 
                cursor: (loading || !selectedProject || !title.trim()) ? 'not-allowed' : 'pointer', 
                display: 'flex', 
                justifyContent: 'center', 
                alignItems: 'center', 
                gap: '0.5rem' 
              }}
            >
              <Send size={18} /> {loading ? 'Creating Ticket...' : 'Create Jira Ticket'}
            </button>
          </form>

          <div style={{ marginTop: '2rem', paddingTop: '1rem', borderTop: '1px solid #eee' }}>
            <h3 style={{ marginTop: 0 }}>Bonus: NHI Blog Digest</h3>
            <p style={{ fontSize: '0.9rem', color: '#666' }}>Automatically fetch and summarize the latest blog post from oasis.security.</p>
            <button
              onClick={handleTriggerBlogDigest}
              style={{ padding: '0.5rem 1rem', backgroundColor: '#34a853', color: '#fff', border: 'none', borderRadius: '4px', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              <RefreshCw size={18} /> Trigger Blog Digest
            </button>
          </div>
        </section>

        {/* Right Column: Recent Tickets */}
        <section style={{ backgroundColor: '#fff', padding: '1.5rem', borderRadius: '8px', border: '1px solid #eee', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1rem' }}>
            <h2 style={{ margin: 0 }}>Recent Tickets</h2>
            <button
              onClick={fetchRecentTickets}
              style={{ padding: '0.25rem 0.5rem', border: 'none', background: 'none', color: '#0052cc', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '0.25rem' }}
            >
              <RefreshCw size={14} /> Refresh
            </button>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {recentTickets.length === 0 ? (
              <p style={{ color: '#999', textAlign: 'center', marginTop: '2rem' }}>No tickets found for this project.</p>
            ) : (
              recentTickets.map((ticket) => (
                <div key={ticket.id} style={{ padding: '1rem', border: '1px solid #eee', borderRadius: '4px' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <h4 style={{ margin: '0 0 0.5rem', color: '#333' }}>{ticket.summary}</h4>
                    <a href={ticket.self} target="_blank" rel="noopener noreferrer" style={{ color: '#0052cc' }}>
                      <ExternalLink size={16} />
                    </a>
                  </div>
                  <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '0.5rem' }}>
                    <span style={{ fontSize: '0.7rem', padding: '0.2rem 0.4rem', borderRadius: '4px', backgroundColor: '#deebff', color: '#0747a6', fontWeight: 'bold' }}>{ticket.status}</span>
                    <span style={{ fontSize: '0.7rem', padding: '0.2rem 0.4rem', borderRadius: '4px', backgroundColor: '#eae6ff', color: '#403294', fontWeight: 'bold' }}>{ticket.priority}</span>
                    <span style={{ fontSize: '0.7rem', padding: '0.2rem 0.4rem', borderRadius: '4px', backgroundColor: '#e3fcef', color: '#006644', fontWeight: 'bold' }}>{ticket.issuetype}</span>
                  </div>
                  <div style={{ fontSize: '0.8rem', color: '#888' }}>
                    {ticket.key} • {new Date(ticket.created).toLocaleString()}
                  </div>
                </div>
              ))
            )}
          </div>
        </section>
      </main>
    </>
  );
};

export default MainContent;
