import axios from 'axios';
import type { Token, Project, Ticket, User } from '../models';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export const authApi = {
  login: async (username: string, password: string): Promise<Token> => {
    const params = new URLSearchParams();
    params.append('username', username);
    params.append('password', password);
    const { data } = await api.post<Token>('/token', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return data;
  },
  getCurrentUser: async (): Promise<User> => {
    const { data } = await api.get<User>('/api/v1/users/me');
    return data;
  },
  getJiraAuthUrl: async (): Promise<{ url: string }> => {
    const { data } = await api.get<{ url: string }>('/api/v1/jira/auth/url');
    return data;
  },
  jiraAuthCallback: async (code: string): Promise<unknown> => {
    const { data } = await api.post('/api/v1/jira/auth/callback', null, {
      params: { code }
    });
    return data;
  },
};

export const jiraApi = {
  getProjects: async (): Promise<Project[]> => {
    const { data } = await api.get<Project[]>('/api/v1/jira/projects');
    return data;
  },
  createTicket: async (projectKey: string, summary: string, description: string): Promise<unknown> => {
    const { data } = await api.post('/api/v1/jira/tickets', {
      project_key: projectKey,
      summary,
      description,
    });
    return data;
  },
  getRecentTickets: async (projectKey: string): Promise<Ticket[]> => {
    const { data } = await api.get<Ticket[]>('/api/v1/jira/tickets/recent', {
      params: { project_key: projectKey },
    });
    return data;
  },
  triggerBlogDigest: async (projectKey: string): Promise<unknown> => {
    const { data } = await api.post('/api/v1/jobs/blog-digest', {
      project_key: projectKey,
    });
    return data;
  },
};

export default api;
