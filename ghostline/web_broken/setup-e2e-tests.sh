#!/bin/bash

echo "Setting up E2E tests for GhostLine..."

# Install Playwright
echo "Installing Playwright..."
npm install -D @playwright/test@latest

# Initialize Playwright
echo "Initializing Playwright config..."
npx playwright install

# Create playwright.config.ts
cat > playwright.config.ts << 'EOF'
import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  webServer: {
    command: 'npm run dev',
    port: 3000,
    reuseExistingServer: !process.env.CI,
  },
});
EOF

# Create E2E test directory
mkdir -p e2e

# Create a real E2E test
cat > e2e/project-creation.spec.ts << 'EOF'
import { test, expect } from '@playwright/test';

test.describe('Project Creation E2E', () => {
  test('should create a project end-to-end', async ({ page }) => {
    // This would catch CORS issues, redirects, etc.
    await page.goto('/auth/login');
    
    // Fill in login form
    await page.fill('input[name="email"]', 'test@example.com');
    await page.fill('input[name="password"]', 'password123');
    await page.click('button[type="submit"]');
    
    // Wait for redirect to dashboard
    await page.waitForURL('/dashboard');
    
    // Navigate to create project
    await page.click('a[href="/dashboard/projects/new"]');
    
    // Fill in project details
    await page.fill('input[name="name"]', 'Test Project');
    await page.fill('textarea[name="description"]', 'Test description');
    await page.selectOption('select[name="genre"]', 'fiction');
    
    // Submit and check for success
    await page.click('button[type="submit"]');
    
    // This would catch any CORS errors, 500 errors, etc.
    await expect(page).toHaveURL(/\/dashboard\/projects\/\w+/);
  });

  test('should handle API errors properly', async ({ page }) => {
    // Test with API down
    await page.route('**/api/v1/**', route => route.abort());
    
    await page.goto('/dashboard/projects/new');
    await page.fill('input[name="name"]', 'Test Project');
    await page.click('button[type="submit"]');
    
    // Should show error message
    await expect(page.locator('text=error')).toBeVisible();
  });
});
EOF

# Update package.json scripts
echo "Adding E2E test scripts to package.json..."
npm pkg set scripts.e2e="playwright test"
npm pkg set scripts.e2e:ui="playwright test --ui"
npm pkg set scripts.e2e:debug="playwright test --debug"

echo "E2E test setup complete!"
echo ""
echo "To run E2E tests:"
echo "  npm run e2e         # Run all E2E tests"
echo "  npm run e2e:ui      # Run with UI mode"
echo "  npm run e2e:debug   # Run in debug mode"
echo ""
echo "To run the real integration tests:"
echo "  1. Start the API locally: cd ../api && docker-compose up"
echo "  2. Run tests: npm test -- real-api.test.ts" 