import axios from 'axios';
import { useAuthStore } from '@/lib/stores/auth';

// For local development, use localhost:8000
// For production, use the environment variable
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor to add auth token
apiClient.interceptors.request.use(
  (config) => {
    const token = useAuthStore.getState().token;
    if (token && token !== 'undefined' && token !== 'null') {
      config.headers.Authorization = `Bearer ${token}`;
    }
    console.log('[API]', config.method?.toUpperCase(), config.url);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    console.error('[API] Response error:', error.response?.status, error.response?.data);
    
    // Don't auto-logout in local dev mode (auth is disabled)
    const isLocalDev = API_BASE_URL.includes('localhost');
    
    if (!isLocalDev && (error.response?.status === 401 || error.response?.status === 403)) {
      const authStore = useAuthStore.getState();
      if (authStore.token) {
        console.log('[API] Authentication error - clearing token');
        authStore.logout();
        if (typeof window !== 'undefined' && !window.location.pathname.includes('/auth/login')) {
          window.location.href = '/auth/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

export default apiClient;

// Helper to check if we're in local dev mode
export const isLocalDev = () => API_BASE_URL.includes('localhost');

// Helper function to handle API errors
export const handleApiError = (error: unknown): string => {
  if (axios.isAxiosError(error)) {
    if (error.response?.data?.detail) {
      return error.response.data.detail;
    }
    switch (error.response?.status) {
      case 500:
        return 'Server error. Please try again later.';
      case 401:
        return 'Authentication required. Please log in.';
      case 403:
        return 'You do not have permission to perform this action.';
      case 404:
        return 'Resource not found.';
      default:
        break;
    }
  }
  if (error instanceof Error) {
    return error.message;
  }
  return 'An unexpected error occurred';
};



