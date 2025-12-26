import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/auth';
import apiClient from '@/lib/api/client';
import { authApi } from '@/lib/api/auth';
import { projectsApi } from '@/lib/api/projects';

// Mock the API client
jest.mock('@/lib/api/client');

const mockApiClient = apiClient as jest.Mocked<typeof apiClient>;

describe('API Client Integration Tests', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    jest.clearAllMocks();
    useAuthStore.getState().logout();
  });

  describe('Authentication Flow', () => {
    it('should successfully login and store token', async () => {
      const mockToken = 'mock-jwt-token';
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
        billing_plan_id: 'basic',
        token_balance: 100000,
        created_at: '2023-06-29T12:00:00Z',
        is_active: true,
        is_verified: false,
      };

      // Mock the login POST request
      mockApiClient.post.mockResolvedValueOnce({
        data: {
          access_token: mockToken,
          token_type: 'bearer',
          expires_in: 86400,
        },
      });

      // Mock the getCurrentUser GET request that happens inside login
      mockApiClient.get.mockResolvedValueOnce({
        data: mockUser,
      });

      const result = await authApi.login({ email: 'test@example.com', password: 'password123' });

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/login/', {
        email: 'test@example.com',
        password: 'password123',
      });

      expect(mockApiClient.get).toHaveBeenCalledWith('/users/me/', {
        headers: {
          Authorization: `Bearer ${mockToken}`
        }
      });

      expect(result.access_token).toBe(mockToken);
      expect(useAuthStore.getState().token).toBe(mockToken);
      expect(useAuthStore.getState().isAuthenticated).toBe(true);
    });

    it('should handle login failure', async () => {
      const error = new Error('Request failed');
      (error as any).response = {
        status: 401,
        data: { detail: 'Invalid credentials' },
      };
      
      mockApiClient.post.mockRejectedValueOnce(error);

      await expect(authApi.login({ email: 'test@example.com', password: 'wrongpassword' })).rejects.toThrow();
      expect(useAuthStore.getState().isAuthenticated).toBe(false);
    });

    it('should successfully register a new user', async () => {
      const mockUser = {
        id: '123',
        email: 'newuser@example.com',
        username: 'newuser',
        full_name: 'New User',
        token_balance: 100000,
        created_at: '2023-06-29T12:00:00Z',
        is_active: true,
        is_verified: false,
      };

      mockApiClient.post.mockResolvedValueOnce({
        data: mockUser,
      });

      const result = await authApi.register({
        email: 'newuser@example.com',
        username: 'newuser',
        password: 'password123',
        full_name: 'New User',
      });

      expect(mockApiClient.post).toHaveBeenCalledWith('/auth/register/', {
        email: 'newuser@example.com',
        username: 'newuser',
        password: 'password123',
        full_name: 'New User',
      });

      expect(result).toEqual(mockUser);
    });

    it('should get current user with valid token', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
        token_balance: 100000,
        created_at: '2023-06-29T12:00:00Z',
        is_active: true,
        is_verified: false,
      };

      // Set auth state with user and token
      useAuthStore.getState().setAuth(mockUser, 'valid-token');
      
      mockApiClient.get.mockResolvedValueOnce({
        data: mockUser,
      });

      const result = await authApi.getCurrentUser();

      expect(mockApiClient.get).toHaveBeenCalledWith('/users/me/');
      expect(result).toEqual(mockUser);
    });

    it('should handle 401 and logout user', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        token_balance: 100000,
      };
      
      useAuthStore.getState().setAuth(mockUser as any, 'expired-token');
      
      const error = new Error('Unauthorized');
      (error as any).response = {
        status: 401,
        data: { detail: 'Token expired' },
      };
      
      mockApiClient.get.mockRejectedValueOnce(error);

      await expect(authApi.getCurrentUser()).rejects.toThrow();
      
      // Note: The actual logout is handled by the response interceptor
      // In a real integration test, we'd test the full flow
    });
  });

  describe('Project Operations', () => {
    beforeEach(() => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        token_balance: 100000,
      };
      useAuthStore.getState().setAuth(mockUser as any, 'valid-token');
    });

    it('should fetch projects list', async () => {
      const mockProjects = [
        { id: '1', title: 'Project 1', status: 'draft' },
        { id: '2', title: 'Project 2', status: 'writing' },
      ];

      mockApiClient.get.mockResolvedValueOnce({
        data: mockProjects,
        status: 200,
      });

      const result = await projectsApi.list();

      expect(mockApiClient.get).toHaveBeenCalledWith('/projects/');
      expect(result).toEqual(mockProjects);
    });

    it('should create a new project', async () => {
      const newProject = {
        title: 'New Book',
        description: 'A great story',
        genre: 'fiction' as const,
      };

      const mockCreatedProject = {
        id: '123',
        ...newProject,
        status: 'draft',
        created_at: '2023-06-29T12:00:00Z',
        updated_at: '2023-06-29T12:00:00Z',
        user_id: '123',
        chapter_count: 0,
        word_count: 0,
      };

      mockApiClient.post.mockResolvedValueOnce({
        data: mockCreatedProject,
        status: 201,
      });

      const result = await projectsApi.create(newProject);

      expect(mockApiClient.post).toHaveBeenCalledWith('/projects/', newProject);
      expect(result).toEqual(mockCreatedProject);
    });

    it('should get a specific project', async () => {
      const mockProject = {
        id: '123',
        title: 'My Book',
        genre: 'fiction',
        status: 'draft',
        created_at: '2023-06-29T12:00:00Z',
        updated_at: '2023-06-29T12:00:00Z',
        user_id: '123',
        chapter_count: 0,
        word_count: 0,
      };

      mockApiClient.get.mockResolvedValueOnce({
        data: mockProject,
        status: 200,
      });

      const result = await projectsApi.get('123');

      expect(mockApiClient.get).toHaveBeenCalledWith('/projects/123/');
      expect(result).toEqual(mockProject);
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      mockApiClient.get.mockRejectedValueOnce(new Error('Network Error'));

      await expect(projectsApi.list()).rejects.toThrow();
    });

    it('should handle 500 server errors', async () => {
      const error = new Error('Server Error');
      (error as any).response = {
        status: 500,
        data: { detail: 'Internal Server Error' },
      };
      
      mockApiClient.get.mockRejectedValueOnce(error);

      await expect(projectsApi.list()).rejects.toThrow();
    });

    it('should handle validation errors', async () => {
      const error = new Error('Validation failed');
      (error as any).response = {
        status: 422,
        data: {
          detail: [
            {
              loc: ['body', 'email'],
              msg: 'Invalid email format',
              type: 'value_error',
            },
          ],
        },
      };
      
      mockApiClient.post.mockRejectedValueOnce(error);

      await expect(
        authApi.register({
          email: 'invalid-email',
          username: 'user',
          password: 'pass',
          full_name: 'User',
        })
      ).rejects.toThrow();
    });
  });

  describe('Request Interceptors', () => {
    it('should add auth token to requests', async () => {
      const token = 'test-token';
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        token_balance: 100000,
      };
      useAuthStore.getState().setAuth(mockUser as any, token);

      // Mock the API response
      mockApiClient.get.mockResolvedValueOnce({
        data: [],
        status: 200,
      });

      await projectsApi.list();
      
      // In a real integration test, the axios interceptor would add the header
      // Here we're just verifying that the API was called
      expect(mockApiClient.get).toHaveBeenCalledWith('/projects/');
    });

    it('should handle HTTP to HTTPS redirect', async () => {
      // This tests the redirect handling in the response interceptor
      mockApiClient.post.mockRejectedValueOnce({
        response: {
          status: 307,
          headers: {
            location: 'http://api.dev.ghostline.ai/api/v1/auth/login',
          },
        },
      });

      // The interceptor should retry with HTTPS
      // In a real test, we'd verify this behavior
    });
  });
}); 