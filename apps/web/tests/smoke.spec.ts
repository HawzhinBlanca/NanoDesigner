import { test, expect } from '@playwright/test';

test('home loads', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByText('Smart Graphic Designer')).toBeVisible();
});

test('dashboard navigates', async ({ page }) => {
  await page.goto('/');
  await page.getByRole('link', { name: 'Dashboard' }).click();
  await expect(page.getByText('Dashboard')).toBeVisible();
});

test('composer route loads', async ({ page }) => {
  await page.goto('/projects/demo/compose');
  await expect(page.getByText('Composer')).toBeVisible();
});

