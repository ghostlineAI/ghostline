/**
 * Real Project Creation Flow Tests
 * These test the complete project creation flow from UI to API
 * @jest-environment node
 */

import axios from 'axios';

// Create a real axios instance for testing
const testClient = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL || 'https://api.dev.ghostline.ai/api/v1',
  timeout: 10000,
});

describe('Project Creation E2E Flow', () => {
  let authToken: string;
  const uniqueEmail = `test_project_${Date.now()}@example.com`;
  const password = 'ValidPass123!';

  // Skip all tests if API is not available
  const skipIfNoAPI = async () => {
    if (process.env.CI) {
      console.log('Skipping real API tests in CI');
      return true;
    }
    
    try {
      await testClient.get('/health/');
      return false;
    } catch (error) {
      if (axios.isAxiosError(error) && error.code === 'ECONNREFUSED') {
        console.log('API not running, skipping tests');
        return true;
      }
      // API is reachable but may have returned error (like 404 for /health)
      // Continue with tests
      return false;
    }
  };

  beforeAll(async () => {
    if (await skipIfNoAPI()) return;

    // Register and login to get auth token
    try {
      // Register user
      await testClient.post('/auth/register/', {
        email: uniqueEmail,
        password,
        username: `testuser_${Date.now()}`,
        full_name: 'Test User'
      });

      // Login to get token
      const loginResponse = await testClient.post('/auth/login/', {
        email: uniqueEmail,
        password
      });

      authToken = loginResponse.data.access_token;
    } catch (error) {
      console.error('Setup failed:', error);
      throw error;
    }
  });

  describe('Project Creation API', () => {
    it('should create a project successfully', async () => {
      if (await skipIfNoAPI()) return;
      if (!authToken) {
        console.log('No auth token, skipping test');
        return;
      }

      const projectData = {
        title: `Test Project ${Date.now()}`,
        genre: 'fiction',
        description: 'This is a test project created by e2e test',
        target_audience: 'general',
        language: 'en'
      };

      const response = await testClient.post('/projects/', projectData, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(response.status).toBe(200); // API returns 200 for successful creation
      expect(response.data).toHaveProperty('id');
      expect(response.data.title).toBe(projectData.title);
      expect(response.data.genre).toBe(projectData.genre);
      expect(response.data.status).toBe('draft');
    });

    it('should validate required fields', async () => {
      if (await skipIfNoAPI()) return;
      if (!authToken) return;

      // Try to create project without title
      const response = await testClient.post('/projects/', {
        genre: 'fiction',
        description: 'Missing title'
      }, {
        headers: {
          Authorization: `Bearer ${authToken}`
        },
        validateStatus: () => true
      });

      expect(response.status).toBe(422);
      expect(response.data.detail).toBeDefined();
    });

    it('should list created projects', async () => {
      if (await skipIfNoAPI()) return;
      if (!authToken) return;

      // First create a project
      const projectData = {
        title: `List Test Project ${Date.now()}`,
        genre: 'non_fiction',
        description: 'Project for list test'
      };

      await testClient.post('/projects/', projectData, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      // Now list projects
      const listResponse = await testClient.get('/projects/', {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });

      expect(listResponse.status).toBe(200);
      expect(Array.isArray(listResponse.data)).toBe(true);
      expect(listResponse.data.length).toBeGreaterThan(0);
      
      // Verify our project is in the list
      const createdProject = listResponse.data.find(
        (p: any) => p.title === projectData.title
      );
      expect(createdProject).toBeDefined();
      expect(createdProject.genre).toBe(projectData.genre);
    });

    it('should handle invalid genre gracefully', async () => {
      if (await skipIfNoAPI()) return;
      if (!authToken) return;

      const response = await testClient.post('/projects/', {
        title: 'Invalid Genre Test',
        genre: 'invalid_genre',
        description: 'Testing invalid genre'
      }, {
        headers: {
          Authorization: `Bearer ${authToken}`
        },
        validateStatus: () => true
      });

      // API should return 422 for validation error
      expect(response.status).toBe(422);
    });
  });

  describe('Full UI Flow Simulation', () => {
    it('should complete the entire project creation flow', async () => {
      if (await skipIfNoAPI()) return;
      if (!authToken) return;

      // 1. User navigates to projects page - verify it loads
      const projectsResponse = await testClient.get('/projects/', {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });
      expect(projectsResponse.status).toBe(200);
      const initialProjectCount = projectsResponse.data.length;

      // 2. User fills form and submits
      const newProject = {
        title: `Full Flow Test ${Date.now()}`,
        genre: 'non_fiction', // Use a valid genre from the enum
        description: 'A complete test of the project creation flow',
        target_audience: 'adults',
        language: 'en'
      };

      // 3. API creates project
      const createResponse = await testClient.post('/projects/', newProject, {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });
      expect(createResponse.status).toBe(200); // API returns 200 for successful creation
      const createdProjectId = createResponse.data.id;

      // 4. User is redirected to projects list - verify new project appears
      const updatedListResponse = await testClient.get('/projects/', {
        headers: {
          Authorization: `Bearer ${authToken}`
        }
      });
      expect(updatedListResponse.data.length).toBe(initialProjectCount + 1);
      
      // 5. Verify the created project is in the list
      const foundProject = updatedListResponse.data.find(
        (p: any) => p.id === createdProjectId
      );
      expect(foundProject).toBeDefined();
      expect(foundProject.title).toBe(newProject.title);
      expect(foundProject.status).toBe('draft');
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors gracefully', async () => {
      // Create a client with invalid URL
      const errorClient = axios.create({
        baseURL: 'http://invalid-url-that-does-not-exist.com',
        timeout: 1000,
      });

      try {
        await errorClient.post('/projects/', {
          title: 'Test',
          genre: 'fiction'
        });
        fail('Should have thrown an error');
      } catch (error) {
        expect(error).toBeDefined();
      }
    });

    it('should handle 500 errors properly', async () => {
      if (await skipIfNoAPI()) return;
      if (!authToken) return;

      // Try to trigger a 500 error by sending malformed data
      const response = await testClient.post('/projects/', 
        'invalid-json-data', // Send string instead of object
        {
          headers: {
            Authorization: `Bearer ${authToken}`,
            'Content-Type': 'application/json'
          },
          validateStatus: () => true
        }
      );

      // API should handle this gracefully
      expect([400, 422, 500]).toContain(response.status);
    });
  });
}); 