/**
 * Main Dashboard Component.
 * This is the primary interface for users to connect to Jira, select projects,
 * report NHI findings, and view recent ticket activity.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { jiraApi, authApi } from '../api';
import type { Project, Ticket, User } from '../models';
import { LogOut, RefreshCw, Send, ExternalLink } from 'lucide-react';

const Dashboard: React.FC = () => {
  // --- State Hooks ---
  
  // User and Project data
  const [user, setUser] = useState<User | undefined>(undefined);
  const [projects, setProjects] = useState<Project[]>([]);
  const [selectedProject, setSelectedProject] = useState<string>('');
  
  // Ticket and Finding data
  const [recentTickets, setRecentTickets] = useState<Ticket[]>([]);
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  
  // UI logic states
  const [loading, setLoading] = useState(false);
  const [connectionError, setConnectionError] = useState<string | undefined>(undefined);
  const [findingError, setFindingError] = useState<string | undefined>(undefined);
  
  // Controls visibility of the Jira connection settings panel
  const [showConfig, setShowConfig] = useState(false);
  
  // Ref to track if the OAuth callback has been processed (prevents double-run in StrictMode)
  const callbackProcessed = React.useRef(false);

  const navigate = useNavigate();

  /**
   * Fetches the current user's profile and checks if Jira is connected.
   * If connected, it automatically fetches available projects.
   */
  const fetchUserData = useCallback(async () => {
    try {
      const userData = await authApi.getCurrentUser();
      setUser(userData);
      
      if (userData.jira_config) {
        // Jira is connected, hide config and fetch projects
        setShowConfig(false);
        const projectsData = await jiraApi.getProjects();
        setProjects(projectsData);
        if (projectsData.length > 0) {
          setSelectedProject(projectsData[0].key);
        } else {
          alert("Your Jira workspace has no projects. You will not be able to report findings until a project is created in Jira.");
        }
      } else {
        // Jira is not connected, show the connection prompt
        setShowConfig(true);
      }
    } catch (err: unknown) {
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosError = err as { response: { status: number } };
        // If unauthorized, redirect to login page
        if (axiosError.response?.status === 401) {
          navigate('/login');
          return;
        }
      }
      setConnectionError('Failed to connect to Jira or fetch user data.');
    }
  }, [navigate]);

  /**
   * Completes the Jira OAuth 2.0 flow by sending the authorization code to the backend.
   * @param code The authorization code from Atlassian.
   */
  const handleJiraCallback = useCallback(async (code: string) => {
    // Avoid double processing in development mode
    if (callbackProcessed.current) return;
    callbackProcessed.current = true;
    
    setLoading(true);
    setConnectionError(undefined);
    try {
      await authApi.jiraAuthCallback(code);
      // Clean up URL and refresh local state
      navigate('/dashboard', { replace: true });
      await fetchUserData();
    } catch {
      setConnectionError('Failed to complete Jira connection. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [navigate, fetchUserData]);

  useEffect(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    if (code) {
      handleJiraCallback(code);
    }
  }, [handleJiraCallback]);

  useEffect(() => {
    fetchUserData();
  }, [fetchUserData]);

  /**
   * Initiates the Jira OAuth flow by redirecting the user to Atlassian.
   */
  const handleConnectJira = async () => {
    setLoading(true);
    setConnectionError(undefined);
    try {
      const { url } = await authApi.getJiraAuthUrl();
      // Redirect to Atlassian's consent page
      window.location.href = url;
    } catch {
      setConnectionError('Failed to get Jira authorization URL. Please ensure JIRA_CLIENT_ID is configured.');
      setLoading(false);
    }
  };

  /**
   * Fetches the 10 most recent tickets for the currently selected project.
   */
  const fetchRecentTickets = useCallback(async () => {
    if (!selectedProject) return;
    try {
      const tickets = await jiraApi.getRecentTickets(selectedProject);
      setRecentTickets(tickets);
    } catch {
      console.error('Failed to fetch recent tickets');
    }
  }, [selectedProject]);

  useEffect(() => {
    fetchRecentTickets();
  }, [fetchRecentTickets]);

  /**
   * Handles the submission of a new NHI finding.
   * Creates a ticket in the user's Jira workspace.
   */
  const handleCreateTicket = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedProject || !title || !description) return;
    setLoading(true);
    setFindingError(undefined);
    try {
      await jiraApi.createTicket(selectedProject, title, description);
      // Clear form and refresh list
      setTitle('');
      setDescription('');
      fetchRecentTickets();
    } catch {
      setFindingError('Failed to create ticket. Please check your Jira configuration.');
    } finally {
      setLoading(false);
    }
  };

  /**
   * Manually triggers the background job to scrape and summarize the latest blog post.
   */
  const handleTriggerBlogDigest = async () => {
    if (!selectedProject) return;
    setLoading(true);
    try {
      const response = await jiraApi.triggerBlogDigest(selectedProject) as { status: string; ticket: { key: string } };
      alert(`Success! Created Jira ticket: ${response.ticket.key}`);
      fetchRecentTickets();
    } catch (err: unknown) {
      let message = 'Failed to trigger blog digest job.';
      if (err && typeof err === 'object' && 'response' in err) {
        const error = err as { response: { data: { detail: string } } };
        message = error.response?.data?.detail || message;
      }
      alert(`Error: ${message}`);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Logs the user out by clearing the token and redirecting to the login page.
   */
  const handleLogout = () => {
    localStorage.removeItem('token');
    navigate('/login');
  };

  return (
    <div style={{ padding: '2rem', maxWidth: '1000px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem', paddingBottom: '1rem', borderBottom: '1px solid #eee' }}>
        <div>
          <h1 style={{ margin: 0, color: '#0052cc' }}>IdentityHub NHI Ticket System</h1>
          <p style={{ margin: '0.5rem 0 0', color: '#666' }}>Welcome, {user?.username}</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem' }}>
          <button
            onClick={() => setShowConfig(!showConfig)}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', border: '1px solid #ccc', borderRadius: '4px', backgroundColor: '#fff', cursor: 'pointer' }}
          >
            <RefreshCw size={18} /> {showConfig ? 'Close Settings' : 'Jira Settings'}
          </button>
          <button
            onClick={handleLogout}
            style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', padding: '0.5rem 1rem', border: '1px solid #ccc', borderRadius: '4px', backgroundColor: '#fff', cursor: 'pointer' }}
          >
            <LogOut size={18} /> Logout
          </button>
        </div>
      </header>

      {showConfig ? (
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
      ) : (
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
      )}
    </div>
  );
};

export default Dashboard;
