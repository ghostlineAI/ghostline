import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/auth';
import { authApi } from '@/lib/api/auth';
import { projectsApi } from '@/lib/api/projects';
import '@testing-library/jest-dom';

// Mock API modules
jest.mock('@/lib/api/auth');
jest.mock('@/lib/api/projects');

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

describe('Form Submission Integration Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    useAuthStore.getState().logout();
  });

  describe('Login Form', () => {
    it('should submit login form and handle success', async () => {
      const mockToken = 'mock-jwt-token';
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        full_name: 'Test User',
        token_balance: 100000,
      };

      (authApi.login as jest.Mock).mockResolvedValueOnce({
        access_token: mockToken,
        token_type: 'bearer',
        expires_in: 86400,
      });

      const LoginForm = () => {
        const [loading, setLoading] = React.useState(false);
        const [error, setError] = React.useState('');

        const handleSubmit = async (e: React.FormEvent) => {
          e.preventDefault();
          setLoading(true);
          setError('');
          
          const formData = new FormData(e.target as HTMLFormElement);
          const email = formData.get('email') as string;
          const password = formData.get('password') as string;

          try {
            await authApi.login({ email, password });
            // In real app, would redirect here
          } catch (err) {
            setError('Login failed');
          } finally {
            setLoading(false);
          }
        };

        return (
          <form onSubmit={handleSubmit}>
            <input name="email" type="email" placeholder="Email" required />
            <input name="password" type="password" placeholder="Password" required />
            <button type="submit" disabled={loading}>
              {loading ? 'Logging in...' : 'Login'}
            </button>
            {error && <div role="alert">{error}</div>}
          </form>
        );
      };

      const user = userEvent.setup();

      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      );

      // Fill in form
      await user.type(screen.getByPlaceholderText('Email'), 'test@example.com');
      await user.type(screen.getByPlaceholderText('Password'), 'password123');

      // Submit form
      await user.click(screen.getByText('Login'));

      // Wait for submission to complete
      await waitFor(() => {
        expect(authApi.login).toHaveBeenCalledWith({
          email: 'test@example.com',
          password: 'password123',
        });
      });
    });

    it('should handle login form validation', async () => {
      let validationCalled = false;
      let validationErrors: Record<string, string> = {};

      const LoginForm = () => {
        const validate = (email: string, password: string) => {
          validationCalled = true;
          const errors: Record<string, string> = {};
          
          if (!email.includes('@')) {
            errors.email = 'Invalid email format';
          }
          
          if (password.length < 8) {
            errors.password = 'Password must be at least 8 characters';
          }
          
          validationErrors = errors;
          return errors;
        };

        const handleSubmit = (e: React.FormEvent) => {
          e.preventDefault();
          const formData = new FormData(e.target as HTMLFormElement);
          const email = formData.get('email') as string;
          const password = formData.get('password') as string;
          
          validate(email, password);
        };

        return (
          <form onSubmit={handleSubmit}>
            <input name="email" placeholder="Email" />
            <input name="password" type="password" placeholder="Password" />
            <button type="submit">Login</button>
          </form>
        );
      };

      const user = userEvent.setup();

      render(
        <TestWrapper>
          <LoginForm />
        </TestWrapper>
      );

      // Submit with invalid data
      await user.type(screen.getByPlaceholderText('Email'), 'invalid-email');
      await user.type(screen.getByPlaceholderText('Password'), 'short');
      await user.click(screen.getByText('Login'));

      // Check validation was called and errors were set
      await waitFor(() => {
        expect(validationCalled).toBe(true);
        expect(validationErrors.email).toBe('Invalid email format');
        expect(validationErrors.password).toBe('Password must be at least 8 characters');
      });
    });
  });

  describe('Registration Form', () => {
    it('should submit registration form with all fields', async () => {
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

      (authApi.register as jest.Mock).mockResolvedValueOnce(mockUser);

      const RegisterForm = () => {
        const [success, setSuccess] = React.useState(false);

        const handleSubmit = async (e: React.FormEvent) => {
          e.preventDefault();
          const formData = new FormData(e.target as HTMLFormElement);
          
          await authApi.register({
            email: formData.get('email') as string,
            username: formData.get('username') as string,
            password: formData.get('password') as string,
            full_name: formData.get('fullName') as string,
          });
          
          setSuccess(true);
        };

        if (success) {
          return <div>Registration successful!</div>;
        }

        return (
          <form onSubmit={handleSubmit}>
            <input name="email" type="email" placeholder="Email" required />
            <input name="username" type="text" placeholder="Username" required />
            <input name="password" type="password" placeholder="Password" required />
            <input name="fullName" type="text" placeholder="Full Name" />
            <button type="submit">Register</button>
          </form>
        );
      };

      const user = userEvent.setup();

      render(
        <TestWrapper>
          <RegisterForm />
        </TestWrapper>
      );

      // Fill in all fields
      await user.type(screen.getByPlaceholderText('Email'), 'newuser@example.com');
      await user.type(screen.getByPlaceholderText('Username'), 'newuser');
      await user.type(screen.getByPlaceholderText('Password'), 'SecurePassword123!');
      await user.type(screen.getByPlaceholderText('Full Name'), 'New User');

      // Submit form
      await user.click(screen.getByText('Register'));

      // Wait for success
      await waitFor(() => {
        expect(screen.getByText('Registration successful!')).toBeInTheDocument();
      });

      expect(authApi.register).toHaveBeenCalledWith({
        email: 'newuser@example.com',
        username: 'newuser',
        password: 'SecurePassword123!',
        full_name: 'New User',
      });
    });
  });

  describe('Project Creation Form', () => {
    beforeEach(() => {
      const mockUser = {
        id: '123',
        email: 'test@example.com',
        username: 'testuser',
        token_balance: 100000,
      };
      useAuthStore.getState().setAuth(mockUser as any, 'valid-token');
    });

    it('should submit project creation form', async () => {
      const mockProject = {
        id: '456',
        title: 'My New Book',
        description: 'An exciting story',
        genre: 'fiction',
        status: 'draft',
        created_at: '2023-06-29T12:00:00Z',
        updated_at: '2023-06-29T12:00:00Z',
        user_id: '123',
        chapter_count: 0,
        word_count: 0,
      };

      (projectsApi.create as jest.Mock).mockResolvedValueOnce(mockProject);

      const ProjectForm = () => {
        const [submitted, setSubmitted] = React.useState(false);

        const handleSubmit = async (e: React.FormEvent) => {
          e.preventDefault();
          const formData = new FormData(e.target as HTMLFormElement);
          
          await projectsApi.create({
            title: formData.get('title') as string,
            description: formData.get('description') as string,
            genre: formData.get('genre') as any,
          });
          
          setSubmitted(true);
        };

        if (submitted) {
          return <div>Project created successfully!</div>;
        }

        return (
          <form onSubmit={handleSubmit}>
            <input name="title" type="text" placeholder="Project Title" required />
            <textarea name="description" placeholder="Description" />
            <select name="genre" required>
              <option value="">Select Genre</option>
              <option value="fiction">Fiction</option>
              <option value="non_fiction">Non-Fiction</option>
              <option value="memoir">Biography</option>
            </select>
            <button type="submit">Create Project</button>
          </form>
        );
      };

      const user = userEvent.setup();

      render(
        <TestWrapper>
          <ProjectForm />
        </TestWrapper>
      );

      // Fill in form
      await user.type(screen.getByPlaceholderText('Project Title'), 'My New Book');
      await user.type(screen.getByPlaceholderText('Description'), 'An exciting story');
      await user.selectOptions(screen.getByRole('combobox'), 'fiction');

      // Submit form
      await user.click(screen.getByText('Create Project'));

      // Wait for success
      await waitFor(() => {
        expect(screen.getByText('Project created successfully!')).toBeInTheDocument();
      });

      expect(projectsApi.create).toHaveBeenCalledWith({
        title: 'My New Book',
        description: 'An exciting story',
        genre: 'fiction',
      });
    });

    it('should handle form submission errors', async () => {
      (projectsApi.create as jest.Mock).mockRejectedValueOnce(
        new Error('Project title already exists')
      );

      const ProjectForm = () => {
        const [error, setError] = React.useState('');

        const handleSubmit = async (e: React.FormEvent) => {
          e.preventDefault();
          setError('');
          
          try {
            await projectsApi.create({
              title: 'Duplicate Title',
              genre: 'fiction' as const,
            });
          } catch (err) {
            setError((err as Error).message);
          }
        };

        return (
          <form onSubmit={handleSubmit}>
            <button type="submit">Create Project</button>
            {error && <div role="alert">{error}</div>}
          </form>
        );
      };

      const user = userEvent.setup();

      render(
        <TestWrapper>
          <ProjectForm />
        </TestWrapper>
      );

      // Submit form
      await user.click(screen.getByText('Create Project'));

      // Check error message
      await waitFor(() => {
        expect(screen.getByText('Project title already exists')).toBeInTheDocument();
      });
    });
  });

  describe('File Upload Form', () => {
    it('should handle file upload', async () => {
      const FileUploadForm = () => {
        const [files, setFiles] = React.useState<File[]>([]);
        const [uploaded, setUploaded] = React.useState(false);

        const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
          if (e.target.files) {
            setFiles(Array.from(e.target.files));
          }
        };

        const handleSubmit = async (e: React.FormEvent) => {
          e.preventDefault();
          // Simulate upload
          if (files.length > 0) {
            setUploaded(true);
          }
        };

        if (uploaded) {
          return <div>Files uploaded successfully!</div>;
        }

        return (
          <form onSubmit={handleSubmit}>
            <input
              type="file"
              onChange={handleFileChange}
              multiple
              accept=".pdf,.doc,.docx,.txt"
            />
            {files.length > 0 && (
              <div>
                <p>{files.length} file(s) selected</p>
                <ul>
                  {files.map((file, index) => (
                    <li key={index}>{file.name}</li>
                  ))}
                </ul>
              </div>
            )}
            <button type="submit" disabled={files.length === 0}>
              Upload Files
            </button>
          </form>
        );
      };

      const user = userEvent.setup();

      const { container } = render(
        <TestWrapper>
          <FileUploadForm />
        </TestWrapper>
      );

      // Create mock files
      const file1 = new File(['content1'], 'document1.pdf', { type: 'application/pdf' });
      const file2 = new File(['content2'], 'document2.txt', { type: 'text/plain' });

      // Upload files
      const input = container.querySelector('input[type="file"]') as HTMLInputElement;
      fireEvent.change(input, {
        target: { files: [file1, file2] }
      });

      // Check files are displayed
      expect(screen.getByText('2 file(s) selected')).toBeInTheDocument();
      expect(screen.getByText('document1.pdf')).toBeInTheDocument();
      expect(screen.getByText('document2.txt')).toBeInTheDocument();

      // Submit form
      await user.click(screen.getByText('Upload Files'));

      // Check success message
      await waitFor(() => {
        expect(screen.getByText('Files uploaded successfully!')).toBeInTheDocument();
      });
    });
  });
}); 