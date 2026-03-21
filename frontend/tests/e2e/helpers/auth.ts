import { randomUUID } from 'node:crypto';

import type { Page } from '@playwright/test';

type TestUser = {
  username: string;
  email: string;
  password: string;
};

type MockCurrentUserOptions = {
  jiraConfig?: Record<string, unknown> | null;
};

export const createUniqueUser = (): TestUser => {
  const suffix = randomUUID();
  return {
    username: `user_${suffix}`,
    email: `user_${suffix}@example.com`,
    password: 'password123',
  };
};

export const mockCurrentUser = async (
  page: Page,
  user: TestUser,
  options: MockCurrentUserOptions = {}
): Promise<void> => {
  await page.route('**/api/v1/users/me', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        username: user.username,
        email: user.email,
        jira_config: options.jiraConfig ?? null,
        api_keys: [],
      }),
    });
  });
};
