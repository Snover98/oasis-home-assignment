/**
 * Data models for the Oasis NHI Ticket System Frontend.
 * These interfaces define the shape of data used throughout the application.
 */

export interface JiraConnectionInfo {
  connected: boolean;
  site_url?: string | null;
}

export interface APIKey {
  id: string;
  name: string;
  created_at: string;
}

export interface APIKeyWithSecret extends APIKey {
  key: string;
}

/**
 * Represents a user within the system.
 */
export interface User {
  username: string;
  email: string;
  jira_config?: JiraConnectionInfo | null;
  api_keys: APIKey[];
}

/**
 * Represents a Jira project retrieved from the API.
 */
export interface Project {
  id: string;
  key: string;
  name: string;
}

/**
 * Represents a Jira issue/ticket with display-ready fields.
 */
export interface Ticket {
  id: string;
  key: string;
  self: string;
  summary: string;
  status: string;
  priority: string;
  issuetype: string;
  created: string;
}
