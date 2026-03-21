export const MOCK_PROJECTS = [
  { id: '1', key: 'PROJ', name: 'Project Alpha' },
  { id: '2', key: 'TEST', name: 'Project Beta' },
];

export const MOCK_RECENT_TICKETS_SUCCESS = [
  {
    id: '1',
    key: 'PROJ-1',
    self: 'http://jira.example.com/proj-1',
    summary: 'Ticket 1 Summary',
    status: 'To Do',
    priority: 'High',
    issuetype: 'Story',
    created: '2023-01-01T10:00:00.000Z',
  },
  {
    id: '2',
    key: 'PROJ-2',
    self: 'http://jira.example.com/proj-2',
    summary: 'Ticket 2 Summary',
    status: 'In Progress',
    priority: 'Medium',
    issuetype: 'Bug',
    created: '2023-01-02T11:00:00.000Z',
  },
];

export const MOCK_RECENT_TICKETS_ERROR_NOCACHE = {
  detail: "Failed to connect to Jira API after multiple retries. No cached tickets available."
};
