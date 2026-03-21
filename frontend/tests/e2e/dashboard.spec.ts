import { test, expect } from '@playwright/test';
import { createUniqueUser, mockCurrentUser } from './helpers/auth';

test.describe('Dashboard and Jira Flow', () => {
  test('should redirect to login if not authenticated', async ({ page }) => {
    await page.route('**/api/v1/users/me', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Could not validate credentials' }),
      });
    });

    await page.goto('/dashboard');
    await expect(page).toHaveURL('/login');
  });

  test('should show Jira connection section for a new user', async ({ page }) => {
    const user = createUniqueUser();
    await mockCurrentUser(page, user);

    await page.goto('/dashboard');
    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: 'Jira Connection' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Connect with Atlassian' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'API Keys' })).toBeVisible();
  });

  test('should log out and redirect to login', async ({ page }) => {
    const user = createUniqueUser();
    await mockCurrentUser(page, user);
    await page.route('**/api/v1/auth/logout', async (route) => {
      await route.fulfill({ status: 204 });
    });

    await page.goto('/dashboard');
    await expect(page).toHaveURL('/dashboard');

    await page.click('button:has-text("Logout")');
    await expect(page).toHaveURL('/login');
    expect(await page.evaluate(() => window.localStorage.getItem('token'))).toBeNull();
  });
});
