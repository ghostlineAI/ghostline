/**
 * Real Integration Tests - These make actual HTTP requests
 * to catch issues that mocked tests miss (like CORS, redirects, etc.)
 * @jest-environment node
 */

import axios from 'axios';

// Use a real axios instance, not our wrapped client
const realClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
});

describe('Real API Integration Tests', () => {
  describe('API Endpoint Behavior', () => {
    it('should handle trailing slashes correctly without redirects', async () => {
      // Skip in CI since API might not be running
      if (process.env.CI) {
        console.log('Skipping real API test in CI');
        return;
      }

      try {
        // Test projects endpoint with trailing slash
        const response = await realClient.get('/projects/', {
          validateStatus: (status) => status < 500, // Don't throw on 4xx
        });

        // Should NOT be a redirect
        expect(response.status).not.toBe(307);
        expect(response.status).not.toBe(308);
        
        // Should be 401 (unauthorized) or 200 (if somehow authorized)
        expect([200, 401, 403]).toContain(response.status);
      } catch (error) {
        if (axios.isAxiosError(error) && error.code === 'ECONNREFUSED') {
          console.log('API not running locally, skipping test');
          return;
        }
        throw error;
      }
    });

    it('should redirect without trailing slash (until backend is updated)', async () => {
      if (process.env.CI) {
        console.log('Skipping real API test in CI');
        return;
      }

      try {
        // Currently FastAPI redirects /projects -> /projects/
        // This test documents the current behavior and will fail once backend is fixed
        const response = await realClient.get('/projects', {
          validateStatus: (status) => status < 500,
          maxRedirects: 0, // Don't follow redirects
        });

        // TODO: Once backend is deployed, this should NOT be 307
        // For now, we expect it to redirect
        expect(response.status).toBe(307);
        expect(response.headers.location).toMatch(/\/projects\/$/);
        
        console.log('WARNING: API is still redirecting. Frontend has trailing slashes but backend needs update.');
      } catch (error) {
        if (axios.isAxiosError(error)) {
          if (error.code === 'ECONNREFUSED') {
            console.log('API not running locally, skipping test');
            return;
          }
        }
        throw error;
      }
    });

    it('should have proper CORS headers', async () => {
      if (process.env.CI) {
        console.log('Skipping real API test in CI');
        return;
      }

      try {
        const response = await realClient.options('/projects/', {
          headers: {
            'Origin': 'http://localhost:3000',
            'Access-Control-Request-Method': 'GET',
          },
        });

        // Check CORS headers
        expect(response.headers['access-control-allow-origin']).toBeTruthy();
        expect(response.headers['access-control-allow-methods']).toContain('GET');
      } catch (error) {
        if (axios.isAxiosError(error) && error.code === 'ECONNREFUSED') {
          console.log('API not running locally, skipping test');
          return;
        }
        throw error;
      }
    });
  });

  describe('Auth Flow - Real Requests', () => {
    it('should return proper error for invalid credentials', async () => {
      if (process.env.CI) {
        console.log('Skipping real API test in CI');
        return;
      }

      try {
        const response = await realClient.post('/auth/login/', {
          email: 'invalid@example.com',
          password: 'wrongpassword',
        }, {
          validateStatus: (status) => status < 500,
        });

        expect(response.status).toBe(401);
        expect(response.data).toHaveProperty('detail');
      } catch (error) {
        if (axios.isAxiosError(error) && error.code === 'ECONNREFUSED') {
          console.log('API not running locally, skipping test');
          return;
        }
        throw error;
      }
    });
  });
}); 