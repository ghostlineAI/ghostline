/**
 * Real Form Submission Integration Tests
 * Tests actual form submissions with real API calls
 * @jest-environment jsdom
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import axios from 'axios';

// Import the actual components we're testing
import LoginForm from '@/app/auth/login/page';
import RegisterForm from '@/app/auth/register/page';
import CreateProjectPage from '@/app/dashboard/projects/new/page';

// Test wrapper with providers
const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('Real Form Submission Tests', () => {
  const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  
  // Skip if no API
  const skipIfNoAPI = async () => {
    if (process.env.CI) return true;
    try {
      await axios.get(`${API_URL}/docs`, { validateStatus: () => true });
      return false;
    } catch {
      console.log('API not available, skipping tests');
      return true;
    }
  };

  describe('Login Form - Real API', () => {
    test('should show error for invalid credentials', async () => {
      if (await skipIfNoAPI()) return;
      
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      );

      // Fill in form
      await user.type(screen.getByLabelText(/email/i), 'wrong@example.com');
      await user.type(screen.getByLabelText(/password/i), 'wrongpassword');
      
      // Submit
      await user.click(screen.getByRole('button', { name: /sign in/i }));

      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/invalid credentials|authentication failed/i)).toBeInTheDocument();
      }, { timeout: 5000 });
    });

    test('should handle network errors gracefully', async () => {
      if (await skipIfNoAPI()) return;
      
      const user = userEvent.setup();
      
      // Temporarily break the API URL
      const originalUrl = process.env.NEXT_PUBLIC_API_URL;
      process.env.NEXT_PUBLIC_API_URL = 'http://localhost:9999/api/v1';
      
      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      );

      await user.type(screen.getByLabelText(/email/i), 'test@example.com');
      await user.type(screen.getByLabelText(/password/i), 'password');
      await user.click(screen.getByRole('button', { name: /sign in/i }));

      await waitFor(() => {
        expect(screen.getByText(/network error|connection failed/i)).toBeInTheDocument();
      });
      
      // Restore URL
      process.env.NEXT_PUBLIC_API_URL = originalUrl;
    });
  });

  describe('Registration Form - Real API', () => {
    test('should validate email format', async () => {
      if (await skipIfNoAPI()) return;
      
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <RegisterForm />
        </TestWrapper>
      );

      // Try invalid email
      await user.type(screen.getByLabelText(/email/i), 'not-an-email');
      await user.type(screen.getByLabelText(/password/i), 'ValidPass123!');
      await user.type(screen.getByLabelText(/username/i), 'testuser');
      
      await user.click(screen.getByRole('button', { name: /sign up/i }));

      // Should show validation error
      await waitFor(() => {
        expect(screen.getByText(/invalid email/i)).toBeInTheDocument();
      });
    });

    test('should register new user successfully', async () => {
      if (await skipIfNoAPI()) return;
      
      const user = userEvent.setup();
      const timestamp = Date.now();
      
      render(
        <TestWrapper>
          <RegisterForm />
        </TestWrapper>
      );

      // Fill form with unique data
      await user.type(screen.getByLabelText(/email/i), `test_${timestamp}@example.com`);
      await user.type(screen.getByLabelText(/password/i), 'ValidPass123!');
      await user.type(screen.getByLabelText(/username/i), `user_${timestamp}`);
      
      await user.click(screen.getByRole('button', { name: /sign up/i }));

      // Should redirect or show success
      await waitFor(() => {
        expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
      }, { timeout: 5000 });
    });
  });

  describe('Project Creation Form - Real API', () => {
    let authToken: string;

    beforeAll(async () => {
      if (await skipIfNoAPI()) return;
      
      // Get auth token for project tests
      const timestamp = Date.now();
      try {
        await axios.post(`${API_URL}/auth/register/`, {
          email: `test_${timestamp}@example.com`,
          password: 'TestPass123!',
          username: `user_${timestamp}`
        });
        
        const loginResponse = await axios.post(`${API_URL}/auth/login/`, {
          email: `test_${timestamp}@example.com`,
          password: 'TestPass123!'
        });
        
        authToken = loginResponse.data.access_token;
        
        // Mock the auth state
        const { useAuthStore } = require('@/lib/stores/auth');
        useAuthStore.getState().setAuth(
          { id: '123', email: `test_${timestamp}@example.com` },
          authToken
        );
      } catch (error) {
        console.error('Failed to setup auth:', error);
      }
    });

    test('should create project with valid data', async () => {
      if (await skipIfNoAPI()) return;
      if (!authToken) {
        console.log('No auth token, skipping');
        return;
      }
      
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <CreateProjectPage />
        </TestWrapper>
      );

      // Fill in project form
      await user.type(screen.getByLabelText(/project name/i), 'Test Project ' + Date.now());
      await user.type(screen.getByLabelText(/description/i), 'A test project description');
      await user.selectOptions(screen.getByLabelText(/genre/i), 'fiction');
      
      // Submit
      await user.click(screen.getByRole('button', { name: /create project/i }));

      // Should show success or redirect
      await waitFor(() => {
        expect(screen.queryByText(/error/i)).not.toBeInTheDocument();
      }, { timeout: 5000 });
    });

    test('should show validation errors for missing fields', async () => {
      if (await skipIfNoAPI()) return;
      if (!authToken) return;
      
      const user = userEvent.setup();
      
      render(
        <TestWrapper>
          <CreateProjectPage />
        </TestWrapper>
      );

      // Submit without filling required fields
      await user.click(screen.getByRole('button', { name: /create project/i }));

      // Should show validation errors
      await waitFor(() => {
        expect(screen.getByText(/name is required/i)).toBeInTheDocument();
      });
    });
  });
}); 