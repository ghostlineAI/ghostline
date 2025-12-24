import apiClient, { isLocalDev } from './client';
import { useAuthStore } from '@/lib/stores/auth';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  username: string;
  password: string;
  full_name?: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
}

export interface UserResponse {
  id: string;
  email: string;
  username: string;
  full_name?: string;
  billing_plan_id?: string;
  token_balance: number;
  created_at: string;
  is_active: boolean;
  is_verified: boolean;
}

// Mock user for local development (when auth is disabled on the server)
const mockDevUser: UserResponse = {
  id: '00000000-0000-0000-0000-000000000001',
  email: 'dev@ghostline.local',
  username: 'dev',
  full_name: 'Development User',
  token_balance: 1000000,
  created_at: new Date().toISOString(),
  is_active: true,
  is_verified: true,
};

export const authApi = {
  /**
   * Login user. In local dev mode, this just sets a mock user.
   */
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    if (isLocalDev()) {
      // In local dev, just set the mock user directly
      console.log('[AUTH] Local dev mode - using mock user');
      useAuthStore.getState().setAuth(mockDevUser, 'dev-token');
      return {
        access_token: 'dev-token',
        token_type: 'bearer',
        expires_in: 86400,
      };
    }

    try {
      const response = await apiClient.post('/auth/login/', credentials);
      const data = response.data;
      
      // Fetch user data after successful login
      const userResponse = await apiClient.get('/users/me/', {
        headers: {
          Authorization: `Bearer ${data.access_token}`
        }
      });
      
      useAuthStore.getState().setAuth(userResponse.data, data.access_token);
      return data;
    } catch (error) {
      console.error('[AUTH] Login error:', error);
      throw error;
    }
  },

  /**
   * Register new user.
   */
  async register(data: RegisterData): Promise<UserResponse> {
    if (isLocalDev()) {
      console.log('[AUTH] Local dev mode - mock registration');
      return mockDevUser;
    }
    const response = await apiClient.post('/auth/register/', data);
    return response.data;
  },

  /**
   * Logout user.
   */
  async logout(): Promise<void> {
    useAuthStore.getState().logout();
  },

  /**
   * Get current user. In local dev mode, returns mock user.
   */
  async getCurrentUser(): Promise<UserResponse> {
    if (isLocalDev()) {
      return mockDevUser;
    }
    const response = await apiClient.get('/users/me/');
    return response.data;
  },

  /**
   * Initialize auth for local dev (auto-login without credentials).
   */
  async initLocalDev(): Promise<void> {
    if (isLocalDev()) {
      const authStore = useAuthStore.getState();
      if (!authStore.isAuthenticated) {
        console.log('[AUTH] Auto-authenticating for local dev');
        authStore.setAuth(mockDevUser, 'dev-token');
      }
    }
  },
};


