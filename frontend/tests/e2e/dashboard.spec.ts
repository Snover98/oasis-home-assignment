import { test, expect } from '@playwright/test';

test.describe('Dashboard and Jira Flow', () => {
  test('should redirect to login if not authenticated', async ({ page }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL('/login');
  });

  test('should show Jira connection section for a new user', async ({ page }) => {
    // Go to register page
    await page.goto('/register');
    const randomUser = `user_${Math.floor(Math.random() * 10000)}`;
    await page.fill('input[type="text"]', randomUser);
    await page.fill('input[type="email"]', `${randomUser}@example.com`);
    await page.fill('input[type="password"]', 'pass123');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.getByRole('heading', { name: 'Jira Connection' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Connect with Atlassian' })).toBeVisible();
    await expect(page.getByRole('heading', { name: 'API Keys' })).toBeVisible();
  });

  test('should log out and redirect to login', async ({ page }) => {
    // Log in
    await page.goto('/login');
    await page.fill('input[type="text"]', 'testuser');
    await page.fill('input[type="password"]', 'password');
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');

    // Click logout
    await page.click('button:has-text("Logout")');
    await expect(page).toHaveURL('/login');
  });
});
