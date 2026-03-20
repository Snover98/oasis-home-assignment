import { test, expect } from '@playwright/test';

test.describe('Authentication Flow', () => {
  test('should log in successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');

    // Fill login form
    await page.fill('input[type="text"]', 'testuser');
    await page.fill('input[type="password"]', 'password');
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('IdentityHub NHI');
  });

  test('should show error with invalid credentials', async ({ page }) => {
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

    const randomUser = `user_${Math.floor(Math.random() * 10000)}`;
    await page.fill('input[type="text"]', randomUser);
    await page.fill('input[type="email"]', `${randomUser}@example.com`);
    await page.fill('input[type="password"]', 'newpassword123');
    await page.click('button[type="submit"]');

    // Should redirect to dashboard
    await expect(page).toHaveURL('/dashboard');
    await expect(page.locator('h1')).toContainText('IdentityHub NHI');
  });
});
