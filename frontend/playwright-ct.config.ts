import { defineConfig, devices } from '@playwright/experimental-ct-react';
import react from '@vitejs/plugin-react'; // Import the React plugin

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: './tests/component',
  timeout: 10000,
  snapshotDir: './tests/component/__snapshots__',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',

  // For component tests, Playwright needs to know how to build and serve your components
  use: {
    ctPort: 3100, // Use a specific port for the component test server
    baseURL: 'http://localhost:3100', // Base URL for the component test server

    // Vite-specific configuration for component testing
    ctVite: {
      plugins: [react()], // Use the Vite React plugin
      server: {
        port: 3100, // Ensure Vite uses the same port as ctPort
        host: 'localhost',
      },
      // entryPoint: 'playwright/index.html', // This might be needed if component testing fails to find it
    },
    trace: 'on-first-retry',
    screenshot: 'only-on-failure',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
