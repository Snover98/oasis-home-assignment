import { test, expect } from '@playwright/test';
import { createUniqueUser, mockCurrentUser } from './helpers/auth';

test.describe('End-to-End Jira Integration Flow', () => {
  test('should register a new user, connect to jira (mocked), and display tickets', async ({ page }) => {
    const user = createUniqueUser();
    let jiraConnected = false;

    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({ status: 204 });
    });
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          username: user.username,
          email: user.email,
          jira_config: jiraConnected
            ? {
                connected: true,
                site_url: 'https://mock.jira',
              }
            : null,
          api_keys: [],
        }),
      });
    });

    await page.goto('/register');
    await page.fill('input[type="text"]', user.username);
    await page.fill('input[type="email"]', user.email);
    await page.fill('input[type="password"]', user.password);
    await page.click('button[type="submit"]');

    // Should arrive on dashboard with the connection prompt
    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: 'Jira Connection' })).toBeVisible();

    // --- Step 2: Simulate Jira connection (mocking backend calls) ---
    await page.route('**/api/v1/jira/auth/callback*', async (route) => {
      const url = new URL(route.request().url());
      expect(url.searchParams.get('state')).toBe('mock_oauth_state');
      jiraConnected = true;
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({ status: 'success', site_name: 'Mock Jira Site' }),
      });
    });

    // Mock projects list
    await page.route('**/api/v1/jira/projects', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: '10000', key: 'TEST', name: 'Test Project' }
        ]),
      });
    });

    // Mock recent tickets
    await page.route('**/api/v1/jira/tickets/recent*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '10101',
            key: 'TEST-1',
            summary: 'My Automated Test Ticket',
            status: 'To Do',
            priority: 'Medium',
            issuetype: 'Task',
            created: new Date().toISOString(),
            self: 'https://mock.jira/TEST-1'
          }
        ]),
      });
    });

    await page.goto('/dashboard?code=mock_oauth_code&state=mock_oauth_state');

    // --- Step 3: Verify the dashboard shows the connected view and tickets ---
    // The "Jira Connection" section should be gone
    await expect(page.getByRole('heading', { name: 'Jira Connection' })).not.toBeVisible();
    
    // The "Report NHI Finding" section should be visible
    await expect(page.getByRole('heading', { name: 'Report NHI Finding' })).toBeVisible();

    // Verify the project is selected
    await expect(page.locator('select')).toContainText('Test Project (TEST)');

    // --- Step 4: Verify the tickets are visible ---
    await expect(page.getByRole('heading', { name: 'Recent Tickets' })).toBeVisible();
    await expect(page.locator('h4')).toContainText('My Automated Test Ticket');
    await expect(page.locator('text=TEST-1')).toBeVisible();
  });

  test('should render cached projects and cached tickets during Jira failover', async ({ page }) => {
    const user = createUniqueUser();
    await mockCurrentUser(page, user, {
      jiraConfig: {
        connected: true,
        site_url: 'https://mock.jira',
      },
    });

    await page.route('**/api/v1/jira/projects', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: '10000', key: 'CACHED', name: 'Cached Project' },
        ]),
      });
    });

    await page.route('**/api/v1/jira/tickets/recent*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '20101',
            key: 'CACHED-1',
            summary: 'Cached Jira Ticket',
            status: 'To Do',
            priority: 'Medium',
            issuetype: 'Task',
            created: new Date().toISOString(),
            self: 'https://mock.jira/CACHED-1'
          }
        ]),
      });
    });

    await page.goto('/dashboard');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: 'Report NHI Finding' })).toBeVisible();
    await expect(page.locator('select')).toContainText('Cached Project (CACHED)');
    await expect(page.getByRole('heading', { name: 'Recent Tickets' })).toBeVisible();
    await expect(page.locator('h4')).toContainText('Cached Jira Ticket');
    await expect(page.locator('text=CACHED-1')).toBeVisible();
  });

  test('should allow selecting a cached project and load its cached tickets during failover', async ({ page }) => {
    const user = createUniqueUser();
    await mockCurrentUser(page, user, {
      jiraConfig: {
        connected: true,
        site_url: 'https://mock.jira',
      },
    });

    await page.route('**/api/v1/jira/projects', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: '10000', key: 'CACHEA', name: 'Cached Project A' },
          { id: '10001', key: 'CACHEB', name: 'Cached Project B' },
        ]),
      });
    });

    await page.route('**/api/v1/jira/tickets/recent*', async (route) => {
      const projectKey = new URL(route.request().url()).searchParams.get('project_key');
      const ticketsByProject = {
        CACHEA: [
          {
            id: '30101',
            key: 'CACHEA-1',
            summary: 'Cached Ticket A',
            status: 'To Do',
            priority: 'Low',
            issuetype: 'Task',
            created: new Date().toISOString(),
            self: 'https://mock.jira/CACHEA-1'
          }
        ],
        CACHEB: [
          {
            id: '30102',
            key: 'CACHEB-1',
            summary: 'Cached Ticket B',
            status: 'Done',
            priority: 'High',
            issuetype: 'Bug',
            created: new Date().toISOString(),
            self: 'https://mock.jira/CACHEB-1'
          }
        ],
      };

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(ticketsByProject[projectKey as keyof typeof ticketsByProject] ?? []),
      });
    });

    await page.goto('/dashboard');

    await expect(page.locator('select')).toContainText('Cached Project A (CACHEA)');
    await expect(page.locator('text=CACHEA-1')).toBeVisible();

    await page.selectOption('select', 'CACHEB');

    await expect(page.locator('text=CACHEB-1')).toBeVisible();
    await expect(page.locator('h4')).toContainText('Cached Ticket B');
  });

  test('should load cached Jira data after the Jira config is removed', async ({ page }) => {
    const user = createUniqueUser();
    await mockCurrentUser(page, user, {
      jiraConfig: null,
    });

    await page.route('**/api/v1/jira/projects', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: '10000', key: 'CACHED', name: 'Cached Project' },
        ]),
      });
    });

    await page.route('**/api/v1/jira/tickets/recent*', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          {
            id: '40101',
            key: 'CACHED-1',
            summary: 'Cached Ticket After Disconnect',
            status: 'To Do',
            priority: 'Medium',
            issuetype: 'Task',
            created: new Date().toISOString(),
            self: 'https://mock.jira/CACHED-1'
          }
        ]),
      });
    });

    await page.goto('/dashboard');

    await expect(page.getByRole('heading', { name: 'Report NHI Finding' })).toBeVisible();
    await expect(page.locator('select')).toContainText('Cached Project (CACHED)');
    await expect(page.locator('text=CACHED-1')).toBeVisible();
    await expect(page.locator('text=Jira is disconnected. Showing cached projects and tickets in read-only mode.')).toBeVisible();
    await expect(page.getByRole('button', { name: 'Create Jira Ticket' })).toBeDisabled();
    await expect(page.getByRole('button', { name: 'Trigger Blog Digest' })).toBeDisabled();
  });

  test('should keep the latest project tickets visible when switching projects quickly during failover', async ({ page }) => {
    const user = createUniqueUser();
    await mockCurrentUser(page, user, {
      jiraConfig: null,
    });

    await page.route('**/api/v1/jira/projects', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: '10000', key: 'CACHEA', name: 'Cached Project A' },
          { id: '10001', key: 'CACHEB', name: 'Cached Project B' },
        ]),
      });
    });

    await page.route('**/api/v1/jira/tickets/recent*', async (route) => {
      const projectKey = new URL(route.request().url()).searchParams.get('project_key');

      if (projectKey === 'CACHEA') {
        await new Promise((resolve) => setTimeout(resolve, 250));
      }

      const ticketsByProject = {
        CACHEA: [
          {
            id: '50101',
            key: 'CACHEA-1',
            summary: 'Cached Ticket A',
            status: 'To Do',
            priority: 'Low',
            issuetype: 'Task',
            created: new Date().toISOString(),
            self: 'https://mock.jira/CACHEA-1'
          }
        ],
        CACHEB: [
          {
            id: '50102',
            key: 'CACHEB-1',
            summary: 'Cached Ticket B',
            status: 'Done',
            priority: 'High',
            issuetype: 'Bug',
            created: new Date().toISOString(),
            self: 'https://mock.jira/CACHEB-1'
          }
        ],
      };

      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify(ticketsByProject[projectKey as keyof typeof ticketsByProject] ?? []),
      });
    });

    await page.goto('/dashboard');
    await page.selectOption('select', 'CACHEB');

    await expect(page.locator('text=CACHEB-1')).toBeVisible();
    await expect(page.locator('text=CACHEA-1')).not.toBeVisible();
    await expect(page.locator('h4')).toContainText('Cached Ticket B');
  });

  test('should reject a Jira callback missing OAuth state', async ({ page }) => {
    const user = createUniqueUser();
    await mockCurrentUser(page, user);

    await page.goto('/dashboard?code=mock_oauth_code');

    await expect(page.getByText('Failed to complete Jira connection. Please try again.')).toBeVisible();
    await expect(page.getByRole('heading', { name: 'Jira Connection' })).toBeVisible();
  });
});
