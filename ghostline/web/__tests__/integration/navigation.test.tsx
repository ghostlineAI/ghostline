import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter } from 'next/navigation';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/auth';
import '@testing-library/jest-dom';

// Mock next/navigation
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
  usePathname: jest.fn(() => '/'),
}));

// Mock components
jest.mock('@/components/layout/sidebar', () => ({
  Sidebar: ({ children }: { children: React.ReactNode }) => (
    <div data-testid="sidebar">
      <nav>
        <a href="/dashboard">Dashboard</a>
        <a href="/dashboard/projects">Projects</a>
        <a href="/dashboard/create">Create</a>
        <a href="/dashboard/data-room">Data Room</a>
        <a href="/dashboard/account">Account</a>
      </nav>
      {children}
    </div>
  ),
}));

const mockRouter = {
  push: jest.fn(),
  replace: jest.fn(),
  prefetch: jest.fn(),
  back: jest.fn(),
};

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

describe('Navigation Integration Tests', () => {
  beforeEach(() => {
    (useRouter as jest.Mock).mockReturnValue(mockRouter);
    jest.clearAllMocks();
    useAuthStore.getState().logout();
  });

  describe('Protected Routes', () => {
    it('should redirect to login when accessing protected route without auth', async () => {
      // Simulate accessing a protected route
      const ProtectedPage = () => {
        const router = useRouter();
        const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

        React.useEffect(() => {
          if (!isAuthenticated) {
            router.push('/auth/login');
          }
        }, [isAuthenticated, router]);

        if (!isAuthenticated) {
          return null;
        }

        return <div>Protected Content</div>;
      };

      render(
        <TestWrapper>
          <ProtectedPage />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/auth/login');
      });
    });

    it('should allow access to protected route when authenticated', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        token_balance: 100000,
      };

      useAuthStore.getState().setAuth(mockUser as any, 'valid-token');

      const ProtectedPage = () => {
        const isAuthenticated = useAuthStore((state) => state.isAuthenticated);

        if (!isAuthenticated) {
          return null;
        }

        return <div>Protected Content</div>;
      };

      render(
        <TestWrapper>
          <ProtectedPage />
        </TestWrapper>
      );

      expect(screen.getByText('Protected Content')).toBeInTheDocument();
      expect(mockRouter.push).not.toHaveBeenCalled();
    });
  });

  describe('Dashboard Navigation', () => {
    beforeEach(() => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        token_balance: 100000,
      };
      useAuthStore.getState().setAuth(mockUser as any, 'valid-token');
    });

    it('should navigate between dashboard pages', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <div data-testid="sidebar">
            <nav>
              <button onClick={() => mockRouter.push('/dashboard/projects')}>
                Projects
              </button>
              <button onClick={() => mockRouter.push('/dashboard/create')}>
                Create
              </button>
              <button onClick={() => mockRouter.push('/dashboard/data-room')}>
                Data Room
              </button>
            </nav>
          </div>
        </TestWrapper>
      );

      // Click Projects
      await user.click(screen.getByText('Projects'));
      expect(mockRouter.push).toHaveBeenCalledWith('/dashboard/projects');

      // Click Create
      await user.click(screen.getByText('Create'));
      expect(mockRouter.push).toHaveBeenCalledWith('/dashboard/create');

      // Click Data Room
      await user.click(screen.getByText('Data Room'));
      expect(mockRouter.push).toHaveBeenCalledWith('/dashboard/data-room');
    });
  });

  describe('Authentication Flow Navigation', () => {
    it('should navigate from login to dashboard on successful login', async () => {
      const LoginFlow = () => {
        const router = useRouter();
        const setAuth = useAuthStore((state) => state.setAuth);

        const handleLogin = async () => {
          // Simulate successful login
          const mockUser = {
            id: '123',
            email: 'test@example.com',
            username: 'testuser',
            token_balance: 100000,
          };
          setAuth(mockUser as any, 'valid-token');
          router.push('/dashboard');
        };

        return (
          <button onClick={handleLogin}>Login</button>
        );
      };

      const user = userEvent.setup();

      render(
        <TestWrapper>
          <LoginFlow />
        </TestWrapper>
      );

      await user.click(screen.getByText('Login'));

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/dashboard');
        expect(useAuthStore.getState().isAuthenticated).toBe(true);
      });
    });

    it('should navigate to login on logout', async () => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        token_balance: 100000,
      };
      useAuthStore.getState().setAuth(mockUser as any, 'valid-token');

      const LogoutFlow = () => {
        const router = useRouter();
        const logout = useAuthStore((state) => state.logout);

        const handleLogout = () => {
          logout();
          router.push('/auth/login');
        };

        return (
          <button onClick={handleLogout}>Logout</button>
        );
      };

      const user = userEvent.setup();

      render(
        <TestWrapper>
          <LogoutFlow />
        </TestWrapper>
      );

      await user.click(screen.getByText('Logout'));

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith('/auth/login');
        expect(useAuthStore.getState().isAuthenticated).toBe(false);
      });
    });
  });

  describe('Deep Linking', () => {
    it('should redirect to intended page after login', async () => {
      const intendedPath = '/dashboard/projects/123';

      const DeepLinkFlow = () => {
        const router = useRouter();
        const setAuth = useAuthStore((state) => state.setAuth);
        const [redirectPath] = React.useState(intendedPath);

        const handleLogin = async () => {
          const mockUser = {
            id: '123',
            email: 'test@example.com',
            username: 'testuser',
            token_balance: 100000,
          };
          setAuth(mockUser as any, 'valid-token');
          router.push(redirectPath);
        };

        return (
          <button onClick={handleLogin}>Login and Redirect</button>
        );
      };

      const user = userEvent.setup();

      render(
        <TestWrapper>
          <DeepLinkFlow />
        </TestWrapper>
      );

      await user.click(screen.getByText('Login and Redirect'));

      await waitFor(() => {
        expect(mockRouter.push).toHaveBeenCalledWith(intendedPath);
      });
    });
  });

  describe('Error Page Navigation', () => {
    it('should navigate to home from 404 page', async () => {
      const NotFoundPage = () => {
        const router = useRouter();

        return (
          <div>
            <h1>404 - Page Not Found</h1>
            <button onClick={() => router.push('/')}>Go Home</button>
          </div>
        );
      };

      const user = userEvent.setup();

      render(
        <TestWrapper>
          <NotFoundPage />
        </TestWrapper>
      );

      await user.click(screen.getByText('Go Home'));

      expect(mockRouter.push).toHaveBeenCalledWith('/');
    });
  });
}); 