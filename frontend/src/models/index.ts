/**
 * Data models for the Oasis NHI Ticket System Frontend.
 * These interfaces define the shape of data used throughout the application.
 */

/**
 * Configuration for a user's Jira connection established via OAuth 2.0.
 */
export interface JiraConfig {
  access_token: string;
  refresh_token?: string;
  cloud_id?: string;
  site_url?: string;
}

/**
 * Represents a user within the system.
 */
export interface User {
  username: string;
  email: string;
  jira_config?: JiraConfig;
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

/**
 * Represents the JWT authentication token received upon successful login.
 */
export interface Token {
  access_token: string;
  token_type: string;
}
