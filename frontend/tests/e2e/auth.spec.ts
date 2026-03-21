import { test, expect } from '@playwright/test';
import { createUniqueUser, mockCurrentUser } from './helpers/auth';

test.describe('Authentication Flow', () => {
  test('should log in successfully with valid credentials', async ({ page }) => {
    const user = createUniqueUser();
    await mockCurrentUser(page, user);
    await page.route('**/token', async (route) => {
      await route.fulfill({ status: 204 });
    });

    await page.goto('/login');
    await page.fill('input[type="text"]', user.username);
    await page.fill('input[type="password"]', user.password);
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('IdentityHub NHI');
    expect(await page.evaluate(() => window.localStorage.getItem('token'))).toBeNull();
  });

  test('should show error with invalid credentials', async ({ page }) => {
    await page.route('**/token', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Incorrect username or password' }),
      });
    });

    await page.goto('/login');

    await page.fill('input[type="text"]', 'wronguser');
    await page.fill('input[type="password"]', 'wrongpass');
    await page.click('button[type="submit"]');

    // Should show error message
    await expect(page.locator('text=Invalid username or password')).toBeVisible();
  });

  test('should register a new user successfully', async ({ page }) => {
    await page.goto('/login');

    // Click Sign up link
    await page.click('text=Sign up');
    await expect(page).toHaveURL('/register');
    await expect(page.locator('h2')).toContainText('Create Account');

    const user = createUniqueUser();
    await mockCurrentUser(page, user);
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({ status: 204 });
    });
    await page.fill('input[type="text"]', user.username);
    await page.fill('input[type="email"]', user.email);
    await page.fill('input[type="password"]', user.password);
    await page.click('button[type="submit"]');

    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('IdentityHub NHI');
    expect(await page.evaluate(() => window.localStorage.getItem('token'))).toBeNull();
  });
});
