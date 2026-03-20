/**
 * Main Dashboard Component.
 * This is the primary interface for users to connect to Jira, select projects,
 * report NHI findings, and view recent ticket activity.
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { jiraApi, authApi } from '../api';
import type { Project, Ticket, User } from '../models';
import { LogOut, RefreshCw } from 'lucide-react';
import JiraConfig from '../components/jira-config';
import { APIKeysManager } from '../components/api-keys-manager';
import MainContent from '../components/main-content';

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
  const handleLogout = async () => {
    try {
      await authApi.logout();
    } catch {
      // Best-effort logout; redirect even if the cookie clear request fails.
    } finally {
      navigate('/login');
    }
  };

  if (!user) {
    return (
      <div style={{ padding: '4rem', textAlign: 'center', fontFamily: 'sans-serif', color: '#666' }}>
        <RefreshCw size={48} className="animate-spin" style={{ marginBottom: '1rem', opacity: 0.5 }} />
        <p>Loading your dashboard...</p>
      </div>
    );
  }

  const renderHeader = () => (
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
  );

  return (
    <div style={{ padding: '2rem', maxWidth: '1000px', margin: '0 auto', fontFamily: 'sans-serif' }}>
      {renderHeader()}
      {showConfig ? (
        <div>
          <JiraConfig 
            loading={loading}
            connectionError={connectionError}
            handleConnectJira={handleConnectJira}
          />
          <APIKeysManager />
        </div>
      ) : (
        <MainContent 
          projects={projects}
          selectedProject={selectedProject}
          setSelectedProject={setSelectedProject}
          title={title}
          setTitle={setTitle}
          description={description}
          setDescription={setDescription}
          loading={loading}
          findingError={findingError}
          recentTickets={recentTickets}
          handleCreateTicket={handleCreateTicket}
          handleTriggerBlogDigest={handleTriggerBlogDigest}
          fetchRecentTickets={fetchRecentTickets}
        />
      )}
    </div>
  );
};

export default Dashboard;
