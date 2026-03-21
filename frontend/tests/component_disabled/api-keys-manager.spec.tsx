import { test, expect } from '@playwright/experimental-ct-react';
import { APIKeysManager } from '../../src/components/api-keys-manager';
import { APIKey } from '../../src/models';

test.describe('APIKeysManager', () => {
  test('should display existing API keys', async ({ mount, page }) => {
    const mockApiKeys: APIKey[] = [
      { id: 'key1', name: 'Test Key 1', created_at: '2023-01-01T10:00:00Z' },
      { id: 'key2', name: 'Test Key 2', created_at: '2023-01-02T11:00:00Z' },
    ];

    await page.route('**/api/v1/api-keys', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify(mockApiKeys),
        headers: { 'Content-Type': 'application/json' },
      });
    });

    const component = await mount(<APIKeysManager />);
    await expect(component.getByText('API Keys')).toBeVisible();
    await expect(component.getByText('Test Key 1')).toBeVisible();
    await expect(component.getByText('Test Key 2')).toBeVisible();
    await expect(component.locator('tbody tr')).toHaveCount(2);
  });

  test('should display "No API keys found" when list is empty', async ({ mount, page }) => {
    await page.route('**/api/v1/api-keys', route => {
      route.fulfill({
        status: 200,
        body: JSON.stringify([]),
        headers: { 'Content-Type': 'application/json' },
      });
    });

    const component = await mount(<APIKeysManager />);
    await expect(component.getByText('API Keys')).toBeVisible();
    await expect(component.getByText('No API keys found.')).toBeVisible();
    await expect(component.locator('tbody tr')).toHaveCount(0); // Ensure no keys are displayed
  });

  test('should display error message when fetching API keys fails', async ({ mount, page }) => {
    await page.route('**/api/v1/api-keys', route => {
      route.fulfill({
        status: 500,
        body: 'Internal Server Error',
        headers: { 'Content-Type': 'text/plain' },
      });
    });

    const component = await mount(<APIKeysManager />);
    await expect(component.getByText('API Keys')).toBeVisible();
    await expect(component.getByText('Failed to load API keys.')).toBeVisible();
    await expect(component.locator('tbody tr')).toHaveCount(0); // Ensure no keys are displayed
  });

  test('should generate a new API key', async ({ mount, page }) => {
    let listCount = 0;
    const mockApiKeys: APIKey[] = [];

    // Mock initial list call
    await page.route('**/api/v1/api-keys', route => {
      listCount++;
      route.fulfill({
        status: 200,
        body: JSON.stringify(mockApiKeys),
        headers: { 'Content-Type': 'application/json' },
      });
    });

    // Mock generate call
    await page.route('POST', '**/api/v1/api-keys', async route => {
      const postData = route.request().postDataJSON();
      const newKey: APIKey = { id: 'newKeyId', name: postData.name, created_at: new Date().toISOString() };
      const newKeyWithSecret = { ...newKey, key: 'sk_test_12345' };
      mockApiKeys.push(newKey); // Add to mock list for subsequent list calls

      route.fulfill({
        status: 200,
        body: JSON.stringify(newKeyWithSecret),
        headers: { 'Content-Type': 'application/json' },
      });
    });

    const component = await mount(<APIKeysManager />);

    // Initial check: no keys
    await expect(component.getByText('No API keys found.')).toBeVisible();
    expect(listCount).toBe(1);

    // Generate new key
    await component.getByPlaceholder('Key Name (e.g., CI/CD Pipeline)').fill('My New Key');
    await component.getByRole('button', { name: 'Generate' }).click();

    // Assert that the new key secret is displayed
    await expect(component.getByText('sk_test_12345')).toBeVisible();
    await expect(component.getByText('Please copy this key now. You will not be able to see it again.')).toBeVisible();

    // Expect another list call after generation
    await expect(component.getByText('My New Key')).toBeVisible(); // Check for the new key in the list
    expect(listCount).toBe(2); // Initial list + refresh after generation
  });

  test('should revoke an API key', async ({ mount, page }) => {
    const mockApiKeys: APIKey[] = [
      { id: 'keyToRevoke', name: 'Key to Revoke', created_at: '2023-01-01T10:00:00Z' },
    ];
    let listCount = 0;

    // Mock initial list call
    await page.route('**/api/v1/api-keys', route => {
      listCount++;
      route.fulfill({
        status: 200,
        body: JSON.stringify(mockApiKeys),
        headers: { 'Content-Type': 'application/json' },
      });
    });

    // Mock revoke call
    await page.route('DELETE', '**/api/v1/api-keys/keyToRevoke', async route => {
      mockApiKeys.pop(); // Simulate removal from list
      route.fulfill({ status: 204 });
    });

    const component = await mount(<APIKeysManager />);

    // Initial check: key is visible
    await expect(component.getByText('Key to Revoke')).toBeVisible();
    expect(listCount).toBe(1);

    // Revoke the key
    page.on('dialog', dialog => dialog.accept()); // Automatically accept confirmation dialog
    await component.getByRole('button', { name: 'Revoke Key' }).click();

    // Expect list to be refreshed and key to be gone
    await expect(component.getByText('Key to Revoke')).not.toBeVisible();
    await expect(component.getByText('No API keys found.')).toBeVisible();
    expect(listCount).toBe(2); // Initial list + refresh after revoke
  });
});
