import { test, expect } from '@playwright/test';
import { createUniqueUser } from './helpers/auth';

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
                cloud_id: 'mock_cloud_id',
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

    await page.goto('/dashboard?code=mock_oauth_code');

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
});
