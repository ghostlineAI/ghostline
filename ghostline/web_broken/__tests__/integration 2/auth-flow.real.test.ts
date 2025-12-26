/**
 * Real Authentication Flow Tests
 * These make actual API calls to test the complete auth flow
 * @jest-environment node
 */

import axios from 'axios';
import { authApi } from '@/lib/api/auth';

// Create a real axios instance for testing
const testClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1',
  timeout: 10000,
});

// Test credentials - in production, these would come from env vars
const TEST_USER = {
  email: 'test@example.com',
  password: 'testpass123',
  username: 'testuser',
  full_name: 'Test User'
};

describe('Real Authentication Flow', () => {
  // Skip all tests if API is not available
  const skipIfNoAPI = async () => {
    if (process.env.CI) {
      console.log('Skipping real API tests in CI');
      return true;
    }
    
    try {
      await testClient.get('/health/'); // Most APIs have a health check
      return false;
    } catch (error) {
      if (axios.isAxiosError(error) && error.code === 'ECONNREFUSED') {
        console.log('API not running locally, skipping tests');
        return true;
      }
      return false;
    }
  };

  describe('Registration Flow', () => {
    it('should handle registration errors properly', async () => {
      if (await skipIfNoAPI()) return;

      try {
        // Try to register with invalid data
        const response = await testClient.post('/auth/register/', {
          email: 'invalid-email',
          password: '123', // Too short
          username: '',
        }, {
          validateStatus: () => true, // Don't throw on 4xx/5xx
        });

        expect(response.status).toBe(422); // Validation error
        expect(response.data).toHaveProperty('detail');
      } catch (error) {
        console.error('Test failed:', error);
        throw error;
      }
    });

    it('should register a new user successfully', async () => {
      if (await skipIfNoAPI()) return;

      // Generate unique email for this test run
      const uniqueEmail = `test_${Date.now()}@example.com`;
      
      try {
        const response = await testClient.post('/auth/register/', {
          email: uniqueEmail,
          password: 'ValidPass123!',
          username: `testuser_${Date.now()}`,
          full_name: 'Test User'
        });

        expect(response.status).toBe(200);  // API returns 200 for successful registration
        expect(response.data).toHaveProperty('id');
        expect(response.data.email).toBe(uniqueEmail);
        expect(response.data.is_active).toBe(true);
        expect(response.data.is_verified).toBe(false); // Email not verified yet
      } catch (error) {
        if (axios.isAxiosError(error)) {
          console.error('Registration failed:', error.response?.data);
        }
        throw error;
      }
    });
  });

  describe('Login Flow', () => {
    it('should reject invalid credentials', async () => {
      if (await skipIfNoAPI()) return;

      const response = await testClient.post('/auth/login/', {
        email: 'nonexistent@example.com',
        password: 'wrongpassword'
      }, {
        validateStatus: () => true,
      });

      expect(response.status).toBe(401);
      expect(response.data.detail).toContain('Incorrect');
    });

    it('should login successfully with valid credentials', async () => {
      if (await skipIfNoAPI()) return;

      // First, ensure test user exists
      const uniqueEmail = `test_${Date.now()}@example.com`;
      const password = 'ValidPass123!';
      
      // Register user first
      await testClient.post('/auth/register/', {
        email: uniqueEmail,
        password,
        username: `testuser_${Date.now()}`,
        full_name: 'Test User'
      });

      // Now try to login
      const loginResponse = await testClient.post('/auth/login/', {
        email: uniqueEmail,
        password
      });

      expect(loginResponse.status).toBe(200);
      expect(loginResponse.data).toHaveProperty('access_token');
      expect(loginResponse.data.token_type).toBe('bearer');
      
      // Verify token works
      const token = loginResponse.data.access_token;
      const meResponse = await testClient.get('/users/me/', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      expect(meResponse.status).toBe(200);
      expect(meResponse.data.email).toBe(uniqueEmail);
    });
  });

  describe('Protected Routes', () => {
    it('should reject requests without auth token', async () => {
      if (await skipIfNoAPI()) return;

      const response = await testClient.get('/projects/', {
        validateStatus: () => true,
      });

      expect(response.status).toBe(403);  // API returns 403 for missing auth
    });

    it('should accept requests with valid auth token', async () => {
      if (await skipIfNoAPI()) return;

      // Get a valid token first
      const uniqueEmail = `test_${Date.now()}@example.com`;
      const password = 'ValidPass123!';
      
      await testClient.post('/auth/register/', {
        email: uniqueEmail,
        password,
        username: `testuser_${Date.now()}`,
      });

      const loginResponse = await testClient.post('/auth/login/', {
        email: uniqueEmail,
        password
      });

      const token = loginResponse.data.access_token;

      // Now make authenticated request
      const response = await testClient.get('/projects/', {
        headers: {
          Authorization: `Bearer ${token}`
        }
      });

      expect(response.status).toBe(200);
      expect(Array.isArray(response.data)).toBe(true);
    });
  });

  describe('CORS Behavior', () => {
    it('should handle preflight requests correctly', async () => {
      if (await skipIfNoAPI()) return;

      const response = await testClient.options('/auth/login/', {
        headers: {
          'Origin': 'http://localhost:3000',
          'Access-Control-Request-Method': 'POST',
          'Access-Control-Request-Headers': 'content-type',
        },
        validateStatus: () => true,
      });

      expect(response.status).toBe(200);
      expect(response.headers['access-control-allow-origin']).toBeTruthy();
      expect(response.headers['access-control-allow-methods']).toContain('POST');
    });
  });
}); 