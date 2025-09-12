import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './pw',
  timeout: 30_000,
  use: {
    baseURL: process.env.API_BASE_URL || 'http://localhost:8080',
    extraHTTPHeaders: {
      'X-Request-ID': `pw-${Date.now()}`
    }
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] }
    }
  ]
});


