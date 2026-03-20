/**
 * API Service layer for the Oasis NHI Ticket System Frontend.
 * Uses Axios for HTTP requests and provides typed methods for all backend endpoints.
 */

import axios from 'axios';
import type { Token, Project, Ticket, User, APIKey, APIKeyWithSecret } from '../models';

/**
 * The base URL for all API requests, loaded from environment variables.
 * Defaults to localhost:8000 for development.
 */
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

/**
 * Root axios instance configured with base URL and credential support.
 */
const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

/**
 * Request interceptor to automatically attach the JWT token from localStorage
 * to the Authorization header of every outgoing request.
 */
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

/**
 * Authentication related API calls.
 */
export const authApi = {
  /**
   * Performs user login and retrieves a JWT token.
   * @param username The user's username.
   * @param password The user's password.
   */
  login: async (username: string, password: string): Promise<Token> => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const { data } = await api.post<Token>('/token', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return data;
  },

  /**
   * Registers a new user and retrieves a JWT token.
   * @param username The new user's username.
   * @param email The new user's email.
   * @param password The new user's password.
   */
  register: async (username: string, email: string, password: string): Promise<Token> => {
    const { data } = await api.post<Token>('/api/v1/auth/register', {
      username,
      email,
      password,
    });
    return data;
  },

  /**
   * Retrieves the current authenticated user's profile.
   */
  getCurrentUser: async (): Promise<User> => {
    const { data } = await api.get<User>('/api/v1/users/me');
    return data;
  },

  /**
   * Fetches the Atlassian OAuth 2.0 authorization URL.
   */
  getJiraAuthUrl: async (): Promise<{ url: string }> => {
    const { data } = await api.get<{ url: string }>('/api/v1/jira/auth/url');
    return data;
  },

  /**
   * Sends the authorization code back to the server to complete the Jira connection.
   * @param code The OAuth authorization code from Atlassian.
   */
  jiraAuthCallback: async (code: string): Promise<unknown> => {
    const { data } = await api.post('/api/v1/jira/auth/callback', null, {
      params: { code }
    });
    return data;
  },
};

/**
 * Jira integration and ticket management API calls.
 */
export const jiraApi = {
  /**
   * Fetches the list of accessible projects from the user's Jira workspace.
   */
  getProjects: async (): Promise<Project[]> => {
    const { data } = await api.get<Project[]>('/api/v1/jira/projects');
    return data;
  },

  /**
   * Creates a new Jira issue/ticket.
   * @param projectKey The project key where the ticket should be created.
   * @param summary The title of the ticket.
   * @param description The detailed content of the ticket.
   */
  createTicket: async (projectKey: string, summary: string, description: string): Promise<unknown> => {
    const { data } = await api.post('/api/v1/jira/tickets', {
      project_key: projectKey,
      summary,
      description,
    });
    return data;
  },

  /**
   * Retrieves the most recent tickets for a specific Jira project.
   * @param projectKey The key of the Jira project to search in.
   */
  getRecentTickets: async (projectKey: string): Promise<Ticket[]> => {
    const { data } = await api.get<Ticket[]>('/api/v1/jira/tickets/recent', {
      params: { project_key: projectKey },
    });
    return data;
  },

  /**
   * Triggers the backend blog digest job for a specific project.
   * @param projectKey The project key where the digest ticket should be created.
   */
  triggerBlogDigest: async (projectKey: string): Promise<unknown> => {
    const { data } = await api.post('/api/v1/jobs/blog-digest', {
      project_key: projectKey,
    });
    return data;
  },
};

/**
 * API Key management calls.
 */
export const apiKeysApi = {
  /**
   * Retrieves all API keys for the current user.
   */
  list: async (): Promise<APIKey[]> => {
    const { data } = await api.get<APIKey[]>('/api/v1/api-keys');
    return data;
  },

  /**
   * Generates a new API key.
   * @param name The name of the API key.
   */
  generate: async (name: string): Promise<APIKeyWithSecret> => {
    const { data } = await api.post<APIKeyWithSecret>('/api/v1/api-keys', { name });
    return data;
  },

  /**
   * Revokes an existing API key.
   * @param id The ID of the API key to revoke.
   */
  revoke: async (id: string): Promise<void> => {
    await api.delete(`/api/v1/api-keys/${id}`);
  },
};

export default api;
