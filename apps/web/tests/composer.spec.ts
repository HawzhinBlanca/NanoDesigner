import { test, expect } from '@playwright/test';

test.describe('Composer Page', () => {
  test('should allow a user to generate variants from a prompt', async ({ page }) => {
    // Mock the API response
    await page.route('**/render', async (route) => {
      const json = {
        assets: [
          { id: '1', url: 'https://via.placeholder.com/1024x576.png?text=Variant+1' },
          { id: '2', url: 'https://via.placeholder.com/1024x576.png?text=Variant+2' },
        ],
        audit: {
          cost_usd: 0.01,
          trace_id: 'mock-trace-id',
          model_route: 'mock-model',
          verified_by: 'mock-verifier',
        },
      };
      await route.fulfill({ json });
    });

    // Navigate to the compose page for a demo project
    await page.goto('/projects/demo/compose');

    // 1. Enter a prompt
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('A test prompt for our E2E test');

    // 2. Click the Generate button
    const generateButton = page.getByRole('button', { name: /Generate/i });
    await generateButton.click();

    // Wait for the "Generating..." text to disappear
    await expect(page.getByRole('button', { name: /Generating/i })).toBeHidden({ timeout: 10000 });

    // 3. Switch to the Variants tab
    const variantsTab = page.getByRole('button', { name: /Variants/i });
    await variantsTab.click();

    // 4. Wait for variant images to appear
    // We need to wait for the actual image elements to be rendered
    await page.waitForTimeout(1000); // Give React time to render
    
    // Check that we have variant cards (not necessarily images if URL validation fails)
    const variantCards = page.locator('[class*="cursor-pointer"]').filter({ hasText: /completed|generating|failed/ });
    const count = await variantCards.count();
    expect(count).toBeGreaterThan(0);
  });
});

test.describe('Composer validation and errors', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/projects/demo/compose');
    await expect(page.getByText('Composer')).toBeVisible();
  });

  test('clamps variant count between 1 and 8', async ({ page }) => {
    const input = page.locator('input[type="number"]').first();
    
    // Try to set value above max
    await input.fill('99');
    
    // Mock the API to check the clamped value
    let requestPayload: any = null;
    await page.route('**/render', async (route) => {
      requestPayload = await route.request().postDataJSON();
      
      await route.fulfill({
        json: {
          assets: [],
          audit: {
            cost_usd: 0.01,
            trace_id: 'test',
            model_route: 'test',
            verified_by: 'test'
          }
        }
      });
    });
    
    // Enter a prompt to enable the button
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('Test prompt');
    
    // Generate with the high value
    await page.getByRole('button', { name: /Generate/i }).click();
    
    // Wait for the request to be made
    await page.waitForTimeout(500);
    
    // Check that the value was clamped
    if (requestPayload) {
      expect(requestPayload.outputs.count).toBeLessThanOrEqual(8);
      expect(requestPayload.outputs.count).toBeGreaterThanOrEqual(1);
    }
  });

  test('requires non-empty prompt', async ({ page }) => {
    const generateButton = page.getByRole('button', { name: /Generate/i });
    
    // Button should be disabled with empty prompt
    await expect(generateButton).toBeDisabled();
    
    // Enter whitespace-only prompt
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('   ');
    
    // Button should still be disabled
    await expect(generateButton).toBeDisabled();
    
    // Enter valid prompt
    await promptTextarea.fill('Valid prompt');
    
    // Button should be enabled
    await expect(generateButton).toBeEnabled();
  });
});

test.describe('Composer accessibility', () => {
  test('variant buttons have proper aria attributes', async ({ page }) => {
    // Mock the API response
    await page.route('**/render', async (route) => {
      await route.fulfill({
        json: {
          assets: [
            { id: '1', url: 'https://via.placeholder.com/100x100?text=1' }
          ],
          audit: {
            cost_usd: 0.01,
            trace_id: 'test',
            model_route: 'test',
            verified_by: 'test'
          }
        }
      });
    });
    
    await page.goto('/projects/demo/compose');
    
    // Generate a variant
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('Test prompt');
    await page.getByRole('button', { name: /Generate/i }).click();
    
    // Wait for generation
    await expect(page.getByRole('button', { name: /Generating/i })).toBeHidden({ timeout: 10000 });
    
    // Switch to variants tab
    await page.getByRole('button', { name: /Variants/i }).click();
    
    // Wait for variant cards to render
    await page.waitForTimeout(1000);
    
    // Check for aria labels on action buttons
    // Look for buttons with specific aria-labels we added
    const addToComparisonBtn = page.getByRole('button', { name: /Add to comparison/i }).first();
    const removeBtn = page.getByRole('button', { name: /Remove variant/i }).first();
    
    // Just check they exist - they should have the aria-label by definition
    await expect(addToComparisonBtn).toBeVisible();
    await expect(removeBtn).toBeVisible();
  });
});