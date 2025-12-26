import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useRouter } from 'next/navigation';
import NewProjectPage from '@/app/dashboard/projects/new/page';
import { projectsApi } from '@/lib/api/projects';
import { useAuthStore } from '@/lib/stores/auth';
import '@testing-library/jest-dom';

// Mock modules
jest.mock('@/lib/api/projects');
jest.mock('next/navigation', () => ({
  useRouter: jest.fn(),
}));
jest.mock('sonner', () => ({
  toast: {
    success: jest.fn(),
    error: jest.fn(),
  },
}));

const TestWrapper = ({ children }: { children: React.ReactNode }) => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });

  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
};

describe('Project Creation E2E Tests', () => {
  const mockPush = jest.fn();
  
  beforeEach(() => {
    jest.clearAllMocks();
    (useRouter as jest.Mock).mockReturnValue({
      push: mockPush,
    });
    
    // Set up authenticated user
    const mockUser = {
      id: '123',
      email: 'test@example.com',
      username: 'testuser',
      token_balance: 100000,
    };
    useAuthStore.getState().setAuth(mockUser as any, 'valid-token');
  });

  it('should successfully create a project with all fields', async () => {
    const mockProject = {
      id: '456',
      name: 'My Amazing Book',
      description: 'A thrilling adventure story',
      genre: 'fiction',
      status: 'draft',
      created_at: '2023-06-29T12:00:00Z',
      updated_at: '2023-06-29T12:00:00Z',
      user_id: '123',
      chapter_count: 0,
      word_count: 0,
    };

    (projectsApi.create as jest.Mock).mockResolvedValueOnce(mockProject);

    const user = userEvent.setup();

    render(
      <TestWrapper>
        <NewProjectPage />
      </TestWrapper>
    );

    // Verify form elements are present
    expect(screen.getByText('Create New Project')).toBeInTheDocument();
    expect(screen.getByLabelText('Project Title *')).toBeInTheDocument();
    expect(screen.getByLabelText('Genre *')).toBeInTheDocument();
    expect(screen.getByLabelText('Description')).toBeInTheDocument();

    // Fill in the form
    await user.type(screen.getByLabelText('Project Title *'), 'My Amazing Book');
    await user.selectOptions(screen.getByLabelText('Genre *'), 'fiction');
    await user.type(screen.getByLabelText('Description'), 'A thrilling adventure story');

    // Submit the form
    await user.click(screen.getByText('Create Project'));

    // Verify API was called with correct data
    await waitFor(() => {
      expect(projectsApi.create).toHaveBeenCalledWith({
        title: 'My Amazing Book',
        description: 'A thrilling adventure story',
        genre: 'fiction',
      });
    });

    // Verify redirect to project detail page
    await waitFor(() => {
      expect(mockPush).toHaveBeenCalledWith('/dashboard/projects/456');
    });
  });

  it('should validate required fields', async () => {
    const user = userEvent.setup();

    render(
      <TestWrapper>
        <NewProjectPage />
      </TestWrapper>
    );

    // Try to submit without filling required fields
    await user.click(screen.getByText('Create Project'));

    // API should not be called
    expect(projectsApi.create).not.toHaveBeenCalled();
  });

  it('should handle API errors gracefully', async () => {
    (projectsApi.create as jest.Mock).mockRejectedValueOnce(
      new Error('Network error')
    );

    const user = userEvent.setup();

    render(
      <TestWrapper>
        <NewProjectPage />
      </TestWrapper>
    );

    // Fill in form
    await user.type(screen.getByLabelText('Project Title *'), 'Test Project');
    await user.selectOptions(screen.getByLabelText('Genre *'), 'fiction');

    // Submit form
    await user.click(screen.getByText('Create Project'));

    // Verify error handling
    await waitFor(() => {
      expect(projectsApi.create).toHaveBeenCalled();
      expect(mockPush).not.toHaveBeenCalled(); // Should not redirect on error
    });
  });

  it('should disable submit button during submission', async () => {
    // Mock a delayed response
    (projectsApi.create as jest.Mock).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    const user = userEvent.setup();

    render(
      <TestWrapper>
        <NewProjectPage />
      </TestWrapper>
    );

    // Fill in form
    await user.type(screen.getByLabelText('Project Title *'), 'Test Project');
    await user.selectOptions(screen.getByLabelText('Genre *'), 'fiction');

    // Submit form
    const submitButton = screen.getByText('Create Project');
    await user.click(submitButton);

    // Button should show loading state
    expect(screen.getByText('Creating...')).toBeInTheDocument();
    expect(submitButton).toBeDisabled();
  });

  it('should handle all genre options correctly', async () => {
    const user = userEvent.setup();

    render(
      <TestWrapper>
        <NewProjectPage />
      </TestWrapper>
    );

    const genreSelect = screen.getByLabelText('Genre *') as HTMLSelectElement;

    // Verify all genre options are available
    const expectedGenres = [
      { value: 'fiction', label: 'Fiction' },
      { value: 'non_fiction', label: 'Non-Fiction' },
      { value: 'memoir', label: 'Biography/Memoir' },
      { value: 'technical', label: 'Technical' },
      { value: 'self_help', label: 'Self-Help' },
      { value: 'business', label: 'Business' },
      { value: 'academic', label: 'Academic' },
      { value: 'other', label: 'Other' },
    ];

    expectedGenres.forEach(({ value, label }) => {
      const option = genreSelect.querySelector(`option[value="${value}"]`);
      expect(option).toBeInTheDocument();
      expect(option).toHaveTextContent(label);
    });
  });

  it('should navigate back when cancel is clicked', async () => {
    const user = userEvent.setup();

    render(
      <TestWrapper>
        <NewProjectPage />
      </TestWrapper>
    );

    await user.click(screen.getByText('Cancel'));

    expect(mockPush).toHaveBeenCalledWith('/dashboard/projects');
  });
}); 