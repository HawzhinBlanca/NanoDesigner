import { test, expect } from '@playwright/test';

const API = process.env.API_BASE_URL || 'http://localhost:8080';

test.describe('Auth through Kong', () => {
  test('missing token -> 401', async ({ request }) => {
    const res = await request.get(`${API}/render`);
    expect(res.status()).toBe(401);
  });

  test('invalid token -> 401', async ({ request }) => {
    const res = await request.get(`${API}/render`, {
      headers: { Authorization: 'Bearer invalid' }
    });
    expect(res.status()).toBe(401);
  });

  test('expired token -> 401', async ({ request }) => {
    // minimal expired JWT (header.payload.sig) is not validated by Kong jwk here; expect 401
    const expired = 'eyJhbGciOiJIUzI1NiJ9.eyJleHAiOjE2MDAwMDAwMDB9.signature';
    const res = await request.get(`${API}/render`, {
      headers: { Authorization: `Bearer ${expired}` }
    });
    expect(res.status()).toBe(401);
  });
});


