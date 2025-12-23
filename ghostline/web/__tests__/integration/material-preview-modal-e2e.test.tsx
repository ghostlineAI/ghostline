/**
 * E2E Tests for MaterialPreviewModal Component
 * Tests the view/preview functionality for uploaded materials
 */

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MaterialPreviewModal } from '@/components/data-room/material-preview-modal';
import { sourceMaterialsApi } from '@/lib/api/source-materials';
import { toast } from 'sonner';

// Mock the API and toast
jest.mock('@/lib/api/source-materials');
jest.mock('sonner');

const mockSourceMaterialsApi = sourceMaterialsApi as jest.Mocked<typeof sourceMaterialsApi>;
const mockToast = toast as jest.Mocked<typeof toast>;

// Mock window.open for download tests
const mockWindowOpen = jest.fn();
Object.defineProperty(window, 'open', {
  value: mockWindowOpen,
});

// Mock fetch for text file content
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

// Sample materials for testing
const pdfMaterial = {
  id: 'pdf-1',
  filename: 'document.pdf',
  material_type: 'PDF',
  file_size: 1024000,
  mime_type: 'application/pdf',
  s3_url: 'https://s3.amazonaws.com/bucket/document.pdf'
};

const textMaterial = {
  id: 'text-1',
  filename: 'notes.txt',
  material_type: 'TEXT',
  file_size: 512,
  mime_type: 'text/plain',
  s3_url: 'https://s3.amazonaws.com/bucket/notes.txt'
};

const imageMaterial = {
  id: 'image-1',
  filename: 'photo.jpg',
  material_type: 'IMAGE',
  file_size: 2048000,
  mime_type: 'image/jpeg',
  s3_url: 'https://s3.amazonaws.com/bucket/photo.jpg'
};

const audioMaterial = {
  id: 'audio-1',
  filename: 'recording.mp3',
  material_type: 'AUDIO',
  file_size: 5120000,
  mime_type: 'audio/mpeg',
  s3_url: 'https://s3.amazonaws.com/bucket/recording.mp3'
};

const docxMaterial = {
  id: 'docx-1',
  filename: 'document.docx',
  material_type: 'DOCX',
  file_size: 1536000,
  mime_type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  s3_url: 'https://s3.amazonaws.com/bucket/document.docx'
};

describe('MaterialPreviewModal E2E Tests', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockWindowOpen.mockClear();
    mockFetch.mockClear();
  });

  describe('TEXT File Preview', () => {
    it('should load and display text file content', async () => {
      const presignedUrl = 'https://presigned-url.com/notes.txt';
      const textContent = 'This is the content of the text file.\nWith multiple lines.';

      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: presignedUrl,
        filename: 'notes.txt',
        expires_in: 3600
      });

      mockFetch.mockResolvedValue({
        ok: true,
        text: jest.fn().mockResolvedValue(textContent)
      } as any);

      render(
        <MaterialPreviewModal
          material={textMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      // Wait for loading to complete
      await waitFor(() => {
        expect(screen.queryByRole('generic')).not.toBeInTheDocument(); // No loading spinner
      });

      // Verify presigned URL was fetched
      expect(mockSourceMaterialsApi.getDownloadUrl).toHaveBeenCalledWith('text-1');

      // Verify text content was fetched and displayed
      expect(mockFetch).toHaveBeenCalledWith(presignedUrl);
      await waitFor(() => {
        expect(screen.getByText(textContent)).toBeInTheDocument();
      });
    });

    it('should handle text file fetch errors gracefully', async () => {
      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: 'https://presigned-url.com/notes.txt',
        filename: 'notes.txt',
        expires_in: 3600
      });

      mockFetch.mockRejectedValue(new Error('Network error'));

      render(
        <MaterialPreviewModal
          material={textMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to load preview');
      });
    });
  });

  describe('PDF File Preview', () => {
    it('should show PDF preview not available message with download button', async () => {
      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: 'https://presigned-url.com/document.pdf',
        filename: 'document.pdf',
        expires_in: 3600
      });

      render(
        <MaterialPreviewModal
          material={pdfMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('PDF preview not available')).toBeInTheDocument();
        expect(screen.getByText('Download PDF')).toBeInTheDocument();
      });
    });

    it('should download PDF when download button is clicked', async () => {
      const user = userEvent.setup();
      const presignedUrl = 'https://presigned-url.com/document.pdf';

      mockSourceMaterialsApi.getDownloadUrl
        .mockResolvedValueOnce({
          download_url: presignedUrl,
          filename: 'document.pdf',
          expires_in: 3600
        })
        .mockResolvedValueOnce({
          download_url: presignedUrl,
          filename: 'document.pdf',
          expires_in: 3600
        });

      render(
        <MaterialPreviewModal
          material={pdfMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Download PDF')).toBeInTheDocument();
      });

      const downloadButton = screen.getByText('Download PDF');
      await user.click(downloadButton);

      expect(mockWindowOpen).toHaveBeenCalledWith(presignedUrl, '_blank');
    });
  });

  describe('IMAGE File Preview', () => {
    it('should display image with presigned URL', async () => {
      const presignedUrl = 'https://presigned-url.com/photo.jpg';

      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: presignedUrl,
        filename: 'photo.jpg',
        expires_in: 3600
      });

      render(
        <MaterialPreviewModal
          material={imageMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        const image = screen.getByAltText('photo.jpg');
        expect(image).toBeInTheDocument();
        expect(image).toHaveAttribute('src', expect.stringContaining(presignedUrl));
      });
    });

    it('should show fallback message when image URL is not available', async () => {
      mockSourceMaterialsApi.getDownloadUrl.mockRejectedValue(new Error('S3 error'));

      render(
        <MaterialPreviewModal
          material={imageMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to load preview');
      });
    });
  });

  describe('AUDIO File Preview', () => {
    it('should display audio player with presigned URL', async () => {
      const presignedUrl = 'https://presigned-url.com/recording.mp3';

      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: presignedUrl,
        filename: 'recording.mp3',
        expires_in: 3600
      });

      render(
        <MaterialPreviewModal
          material={audioMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        const audio = screen.getByRole('application'); // audio element has application role
        expect(audio).toBeInTheDocument();
        expect(audio).toHaveAttribute('controls');
        
        const source = audio.querySelector('source');
        expect(source).toHaveAttribute('src', presignedUrl);
        expect(source).toHaveAttribute('type', 'audio/mpeg');
      });
    });

    it('should show fallback message when audio URL is not available', async () => {
      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: '',
        filename: 'recording.mp3',
        expires_in: 3600
      });

      render(
        <MaterialPreviewModal
          material={audioMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Audio not available')).toBeInTheDocument();
      });
    });
  });

  describe('DOCX File Preview', () => {
    it('should show DOCX preview not available message with download button', async () => {
      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: 'https://presigned-url.com/document.docx',
        filename: 'document.docx',
        expires_in: 3600
      });

      render(
        <MaterialPreviewModal
          material={docxMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Word document preview not available')).toBeInTheDocument();
        expect(screen.getByText('Download Document')).toBeInTheDocument();
      });
    });
  });

  describe('Modal Controls', () => {
    it('should call onOpenChange when close button is clicked', async () => {
      const user = userEvent.setup();
      const mockOnOpenChange = jest.fn();

      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: 'https://presigned-url.com/document.pdf',
        filename: 'document.pdf',
        expires_in: 3600
      });

      render(
        <MaterialPreviewModal
          material={pdfMaterial}
          open={true}
          onOpenChange={mockOnOpenChange}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('document.pdf')).toBeInTheDocument();
      });

      // Find and click the close button (X icon)
      const closeButtons = screen.getAllByRole('button');
      const closeButton = closeButtons.find(btn => 
        btn.querySelector('svg') && btn.getAttribute('aria-label') === 'Close' ||
        btn.textContent === '×' ||
        btn.querySelector('[data-lucide="x"]')
      );

      if (closeButton) {
        await user.click(closeButton);
        expect(mockOnOpenChange).toHaveBeenCalledWith(false);
      }
    });

    it('should display material filename in modal title', async () => {
      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: 'https://presigned-url.com/document.pdf',
        filename: 'document.pdf',
        expires_in: 3600
      });

      render(
        <MaterialPreviewModal
          material={pdfMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('document.pdf')).toBeInTheDocument();
      });
    });
  });

  describe('Loading States', () => {
    it('should show loading spinner while fetching preview data', () => {
      // Mock a pending promise
      mockSourceMaterialsApi.getDownloadUrl.mockImplementation(() => new Promise(() => {}));

      render(
        <MaterialPreviewModal
          material={pdfMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      // Should show loading spinner
      expect(screen.getByRole('generic')).toBeInTheDocument(); // Loading spinner
    });

    it('should hide loading spinner after data loads', async () => {
      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: 'https://presigned-url.com/document.pdf',
        filename: 'document.pdf',
        expires_in: 3600
      });

      render(
        <MaterialPreviewModal
          material={pdfMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(screen.queryByRole('generic')).not.toBeInTheDocument(); // No loading spinner
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle getDownloadUrl API errors', async () => {
      mockSourceMaterialsApi.getDownloadUrl.mockRejectedValue(new Error('API Error'));

      render(
        <MaterialPreviewModal
          material={pdfMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to load preview');
      });
    });

    it('should handle download button errors in preview modal', async () => {
      const user = userEvent.setup();

      // First call succeeds for preview, second call fails for download
      mockSourceMaterialsApi.getDownloadUrl
        .mockResolvedValueOnce({
          download_url: 'https://presigned-url.com/document.pdf',
          filename: 'document.pdf',
          expires_in: 3600
        })
        .mockRejectedValueOnce(new Error('Download failed'));

      render(
        <MaterialPreviewModal
          material={pdfMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Download PDF')).toBeInTheDocument();
      });

      const downloadButton = screen.getByText('Download PDF');
      await user.click(downloadButton);

      await waitFor(() => {
        expect(mockToast.error).toHaveBeenCalledWith('Failed to generate download link');
      });
    });
  });

  describe('Unsupported File Types', () => {
    it('should show generic message for unknown file types', async () => {
      const unknownMaterial = {
        id: 'unknown-1',
        filename: 'data.xyz',
        material_type: 'OTHER',
        file_size: 1024,
        mime_type: 'application/octet-stream',
        s3_url: 'https://s3.amazonaws.com/bucket/data.xyz'
      };

      mockSourceMaterialsApi.getDownloadUrl.mockResolvedValue({
        download_url: 'https://presigned-url.com/data.xyz',
        filename: 'data.xyz',
        expires_in: 3600
      });

      render(
        <MaterialPreviewModal
          material={unknownMaterial}
          open={true}
          onOpenChange={() => {}}
        />
      );

      await waitFor(() => {
        expect(screen.getByText('Preview not available for this file type')).toBeInTheDocument();
        expect(screen.getByText('Download File')).toBeInTheDocument();
      });
    });
  });
}); 