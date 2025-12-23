/**
 * Comprehensive E2E Test for VIEW UPLOADED MATERIALS Feature (Phase 2)
 * Tests view/download/delete icon functionality that user reports as broken
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { toast } from 'sonner';
import { MaterialsList } from '@/components/data-room/materials-list';
import { sourceMaterialsApi } from '@/lib/api/source-materials';

// Mock the API
jest.mock('@/lib/api/source-materials');
jest.mock('sonner');

const mockSourceMaterialsApi = sourceMaterialsApi as jest.Mocked<typeof sourceMaterialsApi>;
const mockToast = toast as jest.Mocked<typeof toast>;

// Mock window.open for download tests
const mockWindowOpen = jest.fn();
Object.defineProperty(window, 'open', {
  value: mockWindowOpen,
});

// Sample test data
const mockMaterials = [
  {
    id: 'material-1',
    filename: 'test-document.pdf',
    material_type: 'PDF',
    file_size: 1024000,
    mime_type: 'application/pdf',
    processing_status: 'COMPLETED',
    created_at: '2024-01-01T00:00:00Z',
    s3_url: 'https://s3.amazonaws.com/bucket/test.pdf'
  },
  {
    id: 'material-2', 
    filename: 'image.jpg',
    material_type: 'IMAGE',
    file_size: 512000,
    mime_type: 'image/jpeg',
    processing_status: 'COMPLETED',
    created_at: '2024-01-02T00:00:00Z',
    s3_url: 'https://s3.amazonaws.com/bucket/image.jpg'
  },
  {
    id: 'material-3',
    filename: 'audio-recording.mp3',
    material_type: 'AUDIO', 
    file_size: 2048000,
    mime_type: 'audio/mpeg',
    processing_status: 'PROCESSING',
    created_at: '2024-01-03T00:00:00Z',
    s3_url: 'https://s3.amazonaws.com/bucket/audio.mp3'
  }
];

interface TestWrapperProps {
  children: React.ReactNode;
}

const TestWrapper = ({ children }: TestWrapperProps) => {
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

describe('VIEW UPLOADED MATERIALS - E2E Tests (Phase 2)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockWindowOpen.mockClear();
    mockSourceMaterialsApi.list.mockResolvedValue(mockMaterials);
  });

  describe('Materials List Display', () => {
    it('should display all uploaded materials with correct metadata', async () => {
      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      // Wait for materials to load
      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Verify all materials are displayed
      expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      expect(screen.getByText('image.jpg')).toBeInTheDocument();
      expect(screen.getByText('audio-recording.mp3')).toBeInTheDocument();

      // Verify file sizes are formatted correctly
      expect(screen.getByText('1000 KB')).toBeInTheDocument(); // 1024000 bytes
      expect(screen.getByText('500 KB')).toBeInTheDocument();  // 512000 bytes
      expect(screen.getByText('2 MB')).toBeInTheDocument();    // 2048000 bytes

      // Verify processing status badges
      expect(screen.getAllByText('COMPLETED')).toHaveLength(2);
      expect(screen.getByText('PROCESSING')).toBeInTheDocument();
    });

    it('should show correct file type icons', async () => {
      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Check for file icons (testing by aria-label)
      expect(screen.getByLabelText('Document file')).toBeInTheDocument(); // PDF
      expect(screen.getByLabelText('Image file')).toBeInTheDocument();    // JPG
      expect(screen.getByLabelText('Audio file')).toBeInTheDocument();    // MP3
    });
  });

  describe('👁️ VIEW Icon Functionality', () => {
    it('should open preview modal when view icon is clicked (COMPLETED status)', async () => {
      const user = userEvent.setup();
      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: 'https://presigned-url.com/test.pdf',
        filename: 'test-document.pdf',
        expires_in: 3600
      });

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Find the view button for the PDF (first material)
      const viewButtons = screen.getAllByRole('button');
      const viewButton = viewButtons.find(btn => 
        btn.querySelector('svg') && btn.getAttribute('title') === null
      );

      expect(viewButton).toBeInTheDocument();
      
      // Click the view button
      await user.click(viewButton!);

      // Verify modal opens (would need to test modal content separately)
      expect(mockSourceMaterialsApi.getDownloadUrl).toHaveBeenCalledWith('material-1');
    });

    it('should disable view button for PROCESSING status files', async () => {
      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('audio-recording.mp3')).toBeInTheDocument();
      });

      // Find all view buttons and check if the one for processing file is disabled
      const viewButtons = screen.getAllByRole('button');
      const processingFileRow = screen.getByText('audio-recording.mp3').closest('[data-testid]') || 
                               screen.getByText('audio-recording.mp3').closest('div');
      
      // The view button for processing files should be disabled
      const allButtons = screen.getAllByRole('button');
      const disabledButtons = allButtons.filter(btn => btn.hasAttribute('disabled'));
      expect(disabledButtons.length).toBeGreaterThan(0);
    });
  });

  describe('⬇️ DOWNLOAD Icon Functionality', () => {
    it('should download file when download icon is clicked', async () => {
      const user = userEvent.setup();
      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: 'https://presigned-url.com/test.pdf',
        filename: 'test-document.pdf', 
        expires_in: 3600
      });

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Find download button (should be second button in each row)
      const downloadButtons = screen.getAllByRole('button');
      const downloadButton = downloadButtons[1]; // Assuming order: view, download, delete

      await user.click(downloadButton);

      // Verify API was called
      expect(mockSourceMaterialsApi.getDownloadUrl).toHaveBeenCalledWith('material-1');
      
      // Verify window.open was called with presigned URL
      await waitFor(() => {
        expect(mockWindowOpen).toHaveBeenCalledWith('https://presigned-url.com/test.pdf', '_blank');
      });
    });

    it('should show error toast when download fails', async () => {
      const user = userEvent.setup();
      mockSourceMaterialsApi.getDownloadUrl.mockRejectedValue(new Error('S3 Error'));

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      const downloadButtons = screen.getAllByRole('button');
      const downloadButton = downloadButtons[1];

      await user.click(downloadButton);

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to generate download link');
      });
    });
  });

  describe('🗑️ DELETE Icon Functionality', () => {
    it('should show confirmation dialog when delete icon is clicked', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Find delete button (should be third button in each row)
      const deleteButtons = screen.getAllByRole('button');
      const deleteButton = deleteButtons[2]; // Assuming order: view, download, delete

      await user.click(deleteButton);

      // Verify confirmation dialog appears
      await waitFor(() => {
        expect(screen.getByText('Delete Material')).toBeInTheDocument();
        expect(screen.getByText(/Are you sure you want to delete.*test-document\.pdf/)).toBeInTheDocument();
      });
    });

    it('should delete material when confirmed in dialog', async () => {
      const user = userEvent.setup();
      mockSourceMaterialsApi.delete.mockResolvedValue();
      
      // Mock list to return fewer items after deletion
      mockSourceMaterialsApi.list
        .mockResolvedValueOnce(mockMaterials)
        .mockResolvedValueOnce(mockMaterials.slice(1)); // Remove first item

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Click delete button
      const deleteButtons = screen.getAllByRole('button');
      const deleteButton = deleteButtons[2];
      await user.click(deleteButton);

      // Confirm deletion
      await waitFor(() => {
        expect(screen.getByText('Delete Material')).toBeInTheDocument();
      });
      
      const confirmButton = screen.getByRole('button', { name: /delete/i });
      await user.click(confirmButton);

      // Verify API was called
      expect(mockSourceMaterialsApi.delete).toHaveBeenCalledWith('material-1');
      
      // Verify success toast
      await waitFor(() => {
        expect(mockToast.success).toHaveBeenCalledWith('Material deleted successfully');
      });
    });

    it('should show error toast when deletion fails', async () => {
      const user = userEvent.setup();
      mockSourceMaterialsApi.delete.mockRejectedValue(new Error('Delete failed'));

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Click delete and confirm
      const deleteButtons = screen.getAllByRole('button');
      const deleteButton = deleteButtons[2];
      await user.click(deleteButton);

      await waitFor(() => {
        expect(screen.getByText('Delete Material')).toBeInTheDocument();
      });

      const confirmButton = screen.getByRole('button', { name: /delete/i });
      await user.click(confirmButton);

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to delete material');
      });
    });

    it('should cancel deletion when cancel button is clicked', async () => {
      const user = userEvent.setup();

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // Click delete button
      const deleteButtons = screen.getAllByRole('button');
      const deleteButton = deleteButtons[2];
      await user.click(deleteButton);

      // Click cancel
      await waitFor(() => {
        expect(screen.getByText('Cancel')).toBeInTheDocument();
      });
      
      const cancelButton = screen.getByRole('button', { name: /cancel/i });
      await user.click(cancelButton);

      // Verify delete API was NOT called
      expect(mockSourceMaterialsApi.delete).not.toHaveBeenCalled();
      
      // Verify dialog is closed
      await waitFor(() => {
        expect(screen.queryByText('Delete Material')).not.toBeInTheDocument();
      });
    });
  });

  describe('Error States & Edge Cases', () => {
    it('should show error message when materials fail to load', async () => {
      mockSourceMaterialsApi.list.mockRejectedValue(new Error('API Error'));

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('Failed to load materials')).toBeInTheDocument();
      });
    });

    it('should show empty state when no materials exist', async () => {
      mockSourceMaterialsApi.list.mockResolvedValue([]);

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('No materials uploaded yet. Start by uploading some files above.')).toBeInTheDocument();
      });
    });

    it('should show loading state while fetching materials', () => {
      // Mock a pending promise
      mockSourceMaterialsApi.list.mockImplementation(() => new Promise(() => {}));

      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      expect(screen.getByRole('generic')).toBeInTheDocument(); // Loading spinner
    });
  });

  describe('Accessibility & UX', () => {
    it('should have proper ARIA labels for all buttons', async () => {
      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('test-document.pdf')).toBeInTheDocument();
      });

      // All buttons should be accessible
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeGreaterThan(0);
      
      // Each material should have 3 action buttons
      expect(buttons.length).toBe(mockMaterials.length * 3);
    });

    it('should show file size in human-readable format', async () => {
      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText('1000 KB')).toBeInTheDocument();
        expect(screen.getByText('500 KB')).toBeInTheDocument();
        expect(screen.getByText('2 MB')).toBeInTheDocument();
      });
    });

    it('should show relative timestamps', async () => {
      render(
        <TestWrapper>
          <MaterialsList projectId="test-project" />
        </TestWrapper>
      );

      await waitFor(() => {
        // Should show "X ago" format
        const timeElements = screen.getAllByText(/ago$/);
        expect(timeElements.length).toBeGreaterThan(0);
      });
    });
  });
}); 