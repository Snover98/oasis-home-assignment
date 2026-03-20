import { test, expect } from '@playwright/test';

test.describe('End-to-End Jira Integration Flow', () => {
  test('should register a new user, connect to jira (mocked), and display tickets', async ({ page }) => {
    // --- Step 1: Register a new user ---
    await page.goto('/register');
    const randomUser = `user_${Math.floor(Math.random() * 10000)}`;
    await page.fill('input[type="text"]', randomUser);
    await page.fill('input[type="email"]', `${randomUser}@example.com`);
    await page.fill('input[type="password"]', 'password123');
    await page.click('button[type="submit"]');

    // Should arrive on dashboard with the connection prompt
    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: 'Jira Connection & API' })).toBeVisible();

    // --- Step 2: Simulate Jira connection (mocking backend calls) ---
    // We mock the callback response because we can't perform a real OAuth handshake
    await page.route('**/api/v1/jira/auth/callback*', async (route) => {
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

    // Mock the user profile to include jira_config so the dashboard switches to "MainContent"
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          username: randomUser,
          email: `${randomUser}@example.com`,
          jira_config: {
            cloud_id: 'mock_cloud_id',
            site_url: 'https://mock.jira'
          }
        }),
      });
    });

    // Simulate the redirect back from Atlassian with a code
    // This triggers the useEffect in Dashboard.tsx that calls jiraAuthCallback
    await page.goto('/dashboard?code=mock_oauth_code');

    // --- Step 3: Verify the dashboard shows the connected view and tickets ---
    // The "Jira Connection" section should be gone
    await expect(page.getByRole('heading', { name: 'Jira Connection & API' })).not.toBeVisible();
    
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
