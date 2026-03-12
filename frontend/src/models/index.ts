export interface JiraConfig {
  access_token: string;
  refresh_token?: string;
  cloud_id?: string;
  site_url?: string;
}

export interface User {
  username: string;
  email: string;
  jira_config?: JiraConfig;
}

export interface Project {
  id: string;
  key: string;
  name: string;
}

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

export interface Token {
  access_token: string;
  token_type: string;
}
