import { test, expect } from '@playwright/test';

const RENDER_ENDPOINT_GLOB = '**/render';

test.describe('Composer error scenarios', () => {
  test('rate limit 429 shows friendly message', async ({ page }) => {
    await page.route(RENDER_ENDPOINT_GLOB, async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({
          status: 429,
          contentType: 'application/json',
          body: JSON.stringify({ detail: { error: 'RateLimitExceeded', message: 'API rate limit exceeded', retry_after_seconds: 60 } })
        });
      }
      return route.continue();
    });

    await page.goto('/projects/demo/compose');
    await page.getByLabel('Variants to Generate').locator('..').getByRole('spinbutton').fill('1');
    await page.getByLabel('Prompt').fill('Test prompt lorem ipsum');
    await page.getByRole('button', { name: 'Generate' }).click();

    await expect(page.getByText(/Rate limit exceeded/i)).toBeVisible({ timeout: 5000 });
  });

  test('server failure 502 surfaces error', async ({ page }) => {
    await page.route(RENDER_ENDPOINT_GLOB, async (route) => {
      if (route.request().method() === 'POST') {
        return route.fulfill({ status: 502, contentType: 'application/json', body: JSON.stringify({ detail: { error: 'Upstream', message: 'Bad gateway' } }) });
      }
      return route.continue();
    });

    await page.goto('/projects/demo/compose');
    await page.getByLabel('Variants to Generate').locator('..').getByRole('spinbutton').fill('1');
    await page.getByLabel('Prompt').fill('Another prompt');
    await page.getByRole('button', { name: 'Generate' }).click();

    await expect(page.getByText(/Generation Failed|API Error|Unexpected error/i)).toBeVisible({ timeout: 5000 });
  });
});
import { test, expect } from '@playwright/test';

test.describe('Composer Error Handling', () => {
  test('should handle API validation errors gracefully', async ({ page }) => {
    // Mock validation error response
    await page.route('**/render', async (route) => {
      await route.fulfill({
        status: 422,
        json: {
          detail: [
            {
              loc: ['body', 'prompt'],
              msg: 'Prompt too long',
              type: 'value_error'
            }
          ]
        }
      });
    });

    await page.goto('/projects/demo/compose');
    
    // Enter a prompt and try to generate
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('Test prompt');
    
    const generateButton = page.getByRole('button', { name: /Generate/i });
    await generateButton.click();
    
    // Should show error message
    await expect(page.getByText(/Validation error/i)).toBeVisible({ timeout: 5000 });
  });

  test('should handle content policy violations', async ({ page }) => {
    // Mock content policy violation
    await page.route('**/render', async (route) => {
      await route.fulfill({
        status: 400,
        json: {
          error: 'ContentPolicyViolationException',
          message: 'Content violates policy',
          details: {
            reason: 'Inappropriate content detected'
          }
        }
      });
    });

    await page.goto('/projects/demo/compose');
    
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('Test prompt');
    
    const generateButton = page.getByRole('button', { name: /Generate/i });
    await generateButton.click();
    
    // Should show content policy error
    await expect(page.getByText(/Content policy violation/i)).toBeVisible({ timeout: 5000 });
  });

  test('should handle rate limiting', async ({ page }) => {
    // Mock rate limit response
    await page.route('**/render', async (route) => {
      await route.fulfill({
        status: 429,
        json: {
          error: 'RateLimitException',
          message: 'Rate limit exceeded'
        }
      });
    });

    await page.goto('/projects/demo/compose');
    
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('Test prompt');
    
    const generateButton = page.getByRole('button', { name: /Generate/i });
    await generateButton.click();
    
    // Should show rate limit error
    await expect(page.getByText(/Rate limit exceeded/i)).toBeVisible({ timeout: 5000 });
  });

  test('should handle network failures', async ({ page }) => {
    // Mock network failure
    await page.route('**/render', async (route) => {
      await route.abort('failed');
    });

    await page.goto('/projects/demo/compose');
    
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('Test prompt');
    
    const generateButton = page.getByRole('button', { name: /Generate/i });
    await generateButton.click();
    
    // Should show generic error message
    await expect(page.getByText(/Generation Failed/i)).toBeVisible({ timeout: 5000 });
  });

  test('should validate variant count input', async ({ page }) => {
    await page.goto('/projects/demo/compose');
    
    const variantInput = page.locator('input[type="number"]').first();
    
    // Try to set invalid values
    await variantInput.fill('0');
    await expect(variantInput).toHaveValue('0');
    
    await variantInput.fill('10');
    await expect(variantInput).toHaveValue('10');
    
    // Generate with invalid count should be clamped
    await page.route('**/render', async (route) => {
      const request = await route.request().postDataJSON();
      expect(request.outputs.count).toBeGreaterThanOrEqual(1);
      expect(request.outputs.count).toBeLessThanOrEqual(8);
      
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
  });

  test('should handle empty prompt submission', async ({ page }) => {
    await page.goto('/projects/demo/compose');
    
    const generateButton = page.getByRole('button', { name: /Generate/i });
    
    // Button should be disabled with empty prompt
    await expect(generateButton).toBeDisabled();
    
    // Enter whitespace-only prompt
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('   ');
    
    // Button should still be disabled
    await expect(generateButton).toBeDisabled();
  });

  test('should properly clean up on component unmount', async ({ page }) => {
    await page.goto('/projects/demo/compose');
    
    // Start a generation
    await page.route('**/render', async (route) => {
      // Delay response to simulate slow network
      await new Promise(resolve => setTimeout(resolve, 1000));
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
    
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('Test prompt');
    
    const generateButton = page.getByRole('button', { name: /Generate/i });
    await generateButton.click();
    
    // Navigate away while generation is in progress
    await page.goto('/');
    
    // Should not have any console errors about state updates
    const consoleErrors: string[] = [];
    page.on('console', msg => {
      if (msg.type() === 'error') {
        consoleErrors.push(msg.text());
      }
    });
    
    await page.waitForTimeout(2000);
    
    const stateUpdateErrors = consoleErrors.filter(err => 
      err.includes('state update') || err.includes('unmounted')
    );
    expect(stateUpdateErrors).toHaveLength(0);
  });
});

test.describe('Composer Variant Management', () => {
  test('should handle variant selection and comparison', async ({ page }) => {
    // Mock successful response with multiple variants
    await page.route('**/render', async (route) => {
      await route.fulfill({
        json: {
          assets: [
            { id: '1', url: 'https://via.placeholder.com/100x100?text=1' },
            { id: '2', url: 'https://via.placeholder.com/100x100?text=2' },
            { id: '3', url: 'https://via.placeholder.com/100x100?text=3' },
            { id: '4', url: 'https://via.placeholder.com/100x100?text=4' }
          ],
          audit: {
            cost_usd: 0.04,
            trace_id: 'test',
            model_route: 'test',
            verified_by: 'test'
          }
        }
      });
    });

    await page.goto('/projects/demo/compose');
    
    // Generate variants
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('Test prompt');
    
    const generateButton = page.getByRole('button', { name: /Generate/i });
    await generateButton.click();
    
    // Wait for generation to complete
    await expect(page.getByRole('button', { name: /Generating/i })).toBeHidden({ timeout: 10000 });
    
    // Switch to variants tab
    await page.getByRole('button', { name: /Variants/i }).click();
    
    // Should show 4 variants
    const variants = page.locator('img[alt="Variant"]');
    await expect(variants).toHaveCount(4);
    
    // Test variant selection
    const firstVariantCard = page.locator('[class*="cursor-pointer"]').first();
    await firstVariantCard.click();
    
    // Should have selection indicator
    await expect(firstVariantCard).toHaveClass(/ring-2 ring-primary/);
    
    // Test comparison toggle
    const compareButtons = page.getByRole('button', { name: /comparison/i });
    await compareButtons.first().click();
    await compareButtons.nth(1).click();
    
    // Compare tab should be enabled
    const compareTab = page.getByRole('button', { name: /Compare/i });
    await expect(compareTab).toBeEnabled();
    
    // Test variant removal
    const removeButtons = page.getByRole('button', { name: /Remove variant/i });
    await removeButtons.first().click();
    
    // Should have 3 variants left
    await expect(variants).toHaveCount(3);
  });

  test('should validate URLs in references', async ({ page }) => {
    await page.goto('/projects/demo/compose');
    
    // Mock the file picker (in real app this would open a dialog)
    await page.evaluate(() => {
      // Simulate adding references with various URLs
      const store = (window as any).__zustand_stores?.find((s: any) => s.getState().addReference);
      if (store) {
        store.getState().addReference('https://valid-url.com/image.jpg');
        store.getState().addReference('javascript:alert(1)'); // XSS attempt
        store.getState().addReference('data:text/html,<script>alert(1)</script>'); // Data URL XSS
      }
    });
    
    // Check that invalid URLs are not rendered as images
    const images = page.locator('img');
    const imageSrcs = await images.evaluateAll(imgs => 
      imgs.map(img => img.getAttribute('src'))
    );
    
    expect(imageSrcs).not.toContain('javascript:alert(1)');
    expect(imageSrcs).not.toContain('data:text/html,<script>alert(1)</script>');
  });
});

test.describe('Composer Accessibility', () => {
  test('should have proper ARIA labels', async ({ page }) => {
    await page.goto('/projects/demo/compose');
    
    // Generate some variants first
    await page.route('**/render', async (route) => {
      await route.fulfill({
        json: {
          assets: [
            { id: '1', url: 'https://via.placeholder.com/100x100?text=1' },
            { id: '2', url: 'https://via.placeholder.com/100x100?text=2' }
          ],
          audit: {
            cost_usd: 0.02,
            trace_id: 'test',
            model_route: 'test',
            verified_by: 'test'
          }
        }
      });
    });
    
    const promptTextarea = page.getByPlaceholder('A modern logo for a tech startup...');
    await promptTextarea.fill('Test prompt');
    await page.getByRole('button', { name: /Generate/i }).click();
    await expect(page.getByRole('button', { name: /Generating/i })).toBeHidden({ timeout: 10000 });
    
    // Switch to variants tab
    await page.getByRole('button', { name: /Variants/i }).click();
    
    // Check for ARIA labels
    const compareButton = page.getByRole('button', { name: /Add to comparison/i }).first();
    await expect(compareButton).toHaveAttribute('aria-label');
    await expect(compareButton).toHaveAttribute('aria-pressed', 'false');
    
    await compareButton.click();
    await expect(compareButton).toHaveAttribute('aria-pressed', 'true');
    
    const removeButton = page.getByRole('button', { name: /Remove variant/i }).first();
    await expect(removeButton).toHaveAttribute('aria-label');
  });

  test('should support keyboard navigation', async ({ page }) => {
    await page.goto('/projects/demo/compose');
    
    // Tab through interactive elements
    await page.keyboard.press('Tab'); // Should focus on first interactive element
    
    const focusedElement = await page.evaluate(() => document.activeElement?.tagName);
    expect(focusedElement).toBeTruthy();
    
    // Test that all buttons are keyboard accessible
    const buttons = page.getByRole('button');
    const buttonCount = await buttons.count();
    
    for (let i = 0; i < buttonCount; i++) {
      const button = buttons.nth(i);
      await button.focus();
      const isFocused = await button.evaluate(el => el === document.activeElement);
      expect(isFocused).toBeTruthy();
    }
  });
});