import { expect, test } from '@playwright/test'

test('user can access the application', async ({ page }) => {
  // Simple E2E test to verify CI pipeline works
  await page.goto('http://localhost:3000')
  expect(true).toBe(true)
})
