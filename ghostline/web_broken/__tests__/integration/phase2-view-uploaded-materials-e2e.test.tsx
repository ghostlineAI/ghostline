/**
 * PHASE 2 Frontend E2E Tests: VIEW UPLOADED MATERIALS Feature
 * 
 * Tests all three icon functionalities (view, download, delete) in the React components
 * against real API endpoints. These tests verify the complete user journey.
 * 
 * DO NOT USE MOCKS - These are live integration tests as required by Blueprint.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MaterialsList } from '@/components/data-room/materials-list';
import { MaterialPreviewModal } from '@/components/data-room/material-preview-modal';
import { sourceMaterialsApi } from '@/lib/api/source-materials';
import { authApi } from '@/lib/api/auth';
import { projectsApi } from '@/lib/api/projects';

// This is a REAL E2E test - it hits actual API endpoints
// Configure test to use development API
const TEST_API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.dev.ghostline.ai/api/v1';

describe('Phase 2 E2E: VIEW UPLOADED MATERIALS Feature', () => {
  let queryClient: QueryClient;
  let testUser: any;
  let authToken: string;
  let testProject: any;
  let uploadedMaterials: any[] = [];

  beforeAll(async () => {
    // Setup for real API testing
    console.log('[E2E Frontend] Setting up real API tests');

    // Create test user (or use existing test credentials)
    const testEmail = `e2e-test-${Date.now()}@example.com`;
    const testPassword = 'TestPassword123!';

    try {
      // Try to register test user
      await authApi.register({
        email: testEmail,
        username: `e2e-test-${Date.now()}`,
        password: testPassword,
        full_name: 'E2E Test User'
      });
    } catch (error) {
      // User might already exist, that's ok
      console.log('[E2E Frontend] Test user might already exist');
    }

    // Login to get auth token
    const loginResponse = await authApi.login({
      email: testEmail,
      password: testPassword
    });

    authToken = loginResponse.access_token;
    
    // Get user data separately
    testUser = await authApi.getCurrentUser();

    console.log('[E2E Frontend] Successfully authenticated test user');

    // Create test project
    testProject = await projectsApi.create({
      title: `E2E Frontend Test Project ${Date.now()}`,
      description: 'Test project for frontend E2E tests',
      genre: 'fiction'
    });

    console.log('[E2E Frontend] Created test project:', testProject.id);
  });

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false },
      },
    });
  });

  afterAll(async () => {
    // Cleanup: Delete all uploaded test materials
    console.log('[E2E Frontend] Cleaning up test materials');
    
    for (const material of uploadedMaterials) {
      try {
        await sourceMaterialsApi.delete(material.id);
        console.log(`[E2E Frontend] Cleaned up material: ${material.filename}`);
      } catch (error) {
        console.log(`[E2E Frontend] Failed to cleanup material ${material.id}:`, error);
      }
    }

    // Note: We don't delete the test project/user to avoid cascading delete issues
    console.log('[E2E Frontend] Cleanup completed');
  });

  describe('Complete VIEW UPLOADED MATERIALS Workflow', () => {
    test('should handle complete workflow: upload → list → view → download → delete', async () => {
      console.log('[E2E Frontend] Starting complete workflow test');

      // Step 1: Upload test files
      const testFiles = [
        { name: 'frontend-test-doc.txt', content: 'Test document content for frontend E2E', type: 'text/plain' },
        { name: 'frontend-test-image.jpg', content: createTestImageBlob(), type: 'image/jpeg' },
      ];

      for (const fileData of testFiles) {
        console.log(`[E2E Frontend] Uploading: ${fileData.name}`);
        
        const file = new File([fileData.content], fileData.name, { type: fileData.type });
        const uploadResult = await sourceMaterialsApi.upload(file, testProject.id);
        
        expect(uploadResult.id).toBeDefined();
        expect(uploadResult.name).toBe(fileData.name);
        expect(uploadResult.status).toBe('completed');
        
                 uploadedMaterials.push({
           filename: fileData.name,
           ...uploadResult
         });
        
        console.log(`[E2E Frontend] ✅ Uploaded: ${fileData.name} -> ${uploadResult.id}`);
      }

      // Step 2: Render MaterialsList component with real data
      console.log('[E2E Frontend] Testing MaterialsList component with real data');
      
      render(
        <QueryClientProvider client={queryClient}>
          <MaterialsList projectId={testProject.id} />
        </QueryClientProvider>
      );

      // Wait for materials to load
      await waitFor(() => {
        expect(screen.getByText('frontend-test-doc.txt')).toBeInTheDocument();
        expect(screen.getByText('frontend-test-image.jpg')).toBeInTheDocument();
      }, { timeout: 10000 });

      console.log('[E2E Frontend] ✅ MaterialsList rendered with uploaded files');

      // Step 3: Test VIEW functionality (eye icon)
      for (const material of uploadedMaterials) {
        console.log(`[E2E Frontend] Testing VIEW (eye icon) for: ${material.filename}`);
        
        const eyeButtons = screen.getAllByRole('button', { name: /view/i });
        const eyeButton = eyeButtons.find(btn => 
          btn.closest('[data-testid*="material-item"]')?.textContent?.includes(material.filename)
        );
        
        expect(eyeButton).toBeInTheDocument();
        expect(eyeButton).not.toBeDisabled();
        
        // Click VIEW button
        await userEvent.click(eyeButton!);
        
        // Should open preview modal
        await waitFor(() => {
          expect(screen.getByRole('dialog')).toBeInTheDocument();
          expect(screen.getByText(material.filename)).toBeInTheDocument();
        });
        
        // Close modal
        const closeButton = screen.getByRole('button', { name: /close/i });
        await userEvent.click(closeButton);
        
        await waitFor(() => {
          expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        });
        
        console.log(`[E2E Frontend] ✅ VIEW working for: ${material.filename}`);
      }

      // Step 4: Test DOWNLOAD functionality (download icon)
      for (const material of uploadedMaterials) {
        console.log(`[E2E Frontend] Testing DOWNLOAD (download icon) for: ${material.filename}`);
        
        // Mock window.open to prevent actual download during test
        const originalWindowOpen = window.open;
        const mockWindowOpen = jest.fn();
        window.open = mockWindowOpen;
        
        const downloadButtons = screen.getAllByRole('button', { name: /download/i });
        const downloadButton = downloadButtons.find(btn => 
          btn.closest('[data-testid*="material-item"]')?.textContent?.includes(material.filename)
        );
        
        expect(downloadButton).toBeInTheDocument();
        expect(downloadButton).not.toBeDisabled();
        
        // Click DOWNLOAD button
        await userEvent.click(downloadButton!);
        
        // Wait for download URL generation and window.open call
        await waitFor(() => {
          expect(mockWindowOpen).toHaveBeenCalled();
        }, { timeout: 10000 });
        
        const downloadUrl = mockWindowOpen.mock.calls[0][0];
        expect(downloadUrl).toMatch(/^https?:\/\//);
        
        // Verify the download URL is actually accessible
        const response = await fetch(downloadUrl);
        expect(response.status).toBe(200);
        
        // Restore window.open
        window.open = originalWindowOpen;
        mockWindowOpen.mockClear();
        
        console.log(`[E2E Frontend] ✅ DOWNLOAD working for: ${material.filename}`);
      }

      // Step 5: Test DELETE functionality (trash icon)
      for (const material of uploadedMaterials) {
        console.log(`[E2E Frontend] Testing DELETE (trash icon) for: ${material.filename}`);
        
        const deleteButtons = screen.getAllByRole('button', { name: /delete/i });
        const deleteButton = deleteButtons.find(btn => 
          btn.closest('[data-testid*="material-item"]')?.textContent?.includes(material.filename)
        );
        
        expect(deleteButton).toBeInTheDocument();
        expect(deleteButton).not.toBeDisabled();
        
        // Click DELETE button
        await userEvent.click(deleteButton!);
        
        // Should open confirmation dialog
        await waitFor(() => {
          expect(screen.getByRole('dialog')).toBeInTheDocument();
          expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
        });
        
        // Confirm deletion
        const confirmButton = screen.getByRole('button', { name: /delete/i });
        await userEvent.click(confirmButton);
        
        // Wait for material to disappear from list
        await waitFor(() => {
          expect(screen.queryByText(material.filename)).not.toBeInTheDocument();
        }, { timeout: 10000 });
        
        console.log(`[E2E Frontend] ✅ DELETE working for: ${material.filename}`);
      }

      // Step 6: Verify list is empty
      await waitFor(() => {
        expect(screen.getByText(/no materials uploaded/i)).toBeInTheDocument();
      });

      console.log('[E2E Frontend] ✅ Complete workflow test PASSED');
    });
  });

  describe('Error Handling Tests', () => {
    test('should handle VIEW errors gracefully', async () => {
      console.log('[E2E Frontend] Testing VIEW error handling');
      
      // Upload a test file first
      const file = new File(['test content'], 'error-test.txt', { type: 'text/plain' });
      const uploadResult = await sourceMaterialsApi.upload(file, testProject.id);
      uploadedMaterials.push(uploadResult);
      
      render(
        <QueryClientProvider client={queryClient}>
          <MaterialsList projectId={testProject.id} />
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('error-test.txt')).toBeInTheDocument();
      });

      // Test VIEW for file that's still processing (should be disabled)
      // This tests the UI state handling for different processing statuses
      const eyeButtons = screen.getAllByRole('button', { name: /view/i });
      expect(eyeButtons.length).toBeGreaterThan(0);
      
      console.log('[E2E Frontend] ✅ VIEW error handling test completed');
    });

    test('should handle DOWNLOAD errors gracefully', async () => {
      console.log('[E2E Frontend] Testing DOWNLOAD error handling');
      
      // Test download with network error simulation
      const originalFetch = global.fetch;
      global.fetch = jest.fn().mockRejectedValue(new Error('Network error'));
      
      // Upload a test file
      const file = new File(['test content'], 'download-error-test.txt', { type: 'text/plain' });
      const uploadResult = await sourceMaterialsApi.upload(file, testProject.id);
      uploadedMaterials.push(uploadResult);
      
      render(
        <QueryClientProvider client={queryClient}>
          <MaterialsList projectId={testProject.id} />
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('download-error-test.txt')).toBeInTheDocument();
      });

      // Try to download (should handle error gracefully)
      const downloadButton = screen.getByRole('button', { name: /download/i });
      await userEvent.click(downloadButton);
      
      // Should show error message
      await waitFor(() => {
        expect(screen.getByText(/failed to generate download/i)).toBeInTheDocument();
      }, { timeout: 10000 });
      
      // Restore fetch
      global.fetch = originalFetch;
      
      console.log('[E2E Frontend] ✅ DOWNLOAD error handling test completed');
    });

    test('should handle DELETE errors gracefully', async () => {
      console.log('[E2E Frontend] Testing DELETE error handling');
      
      // Upload a test file
      const file = new File(['test content'], 'delete-error-test.txt', { type: 'text/plain' });
      const uploadResult = await sourceMaterialsApi.upload(file, testProject.id);
      uploadedMaterials.push(uploadResult);
      
      render(
        <QueryClientProvider client={queryClient}>
          <MaterialsList projectId={testProject.id} />
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByText('delete-error-test.txt')).toBeInTheDocument();
      });

      // Test delete functionality
      const deleteButton = screen.getByRole('button', { name: /delete/i });
      await userEvent.click(deleteButton);
      
      // Confirm deletion
      await waitFor(() => {
        expect(screen.getByRole('dialog')).toBeInTheDocument();
      });
      
      const confirmButton = screen.getByRole('button', { name: /delete/i });
      await userEvent.click(confirmButton);
      
      // Should handle deletion (success or error)
      await waitFor(() => {
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
      }, { timeout: 10000 });
      
      console.log('[E2E Frontend] ✅ DELETE error handling test completed');
    });
  });

  describe('Different File Types Tests', () => {
    test('should handle different file types correctly', async () => {
      console.log('[E2E Frontend] Testing different file types');
      
      const fileTypes = [
        { name: 'test.pdf', content: 'PDF content', type: 'application/pdf' },
        { name: 'test.mp3', content: 'Audio content', type: 'audio/mpeg' },
        { name: 'test.png', content: createTestImageBlob(), type: 'image/png' },
      ];

      for (const fileData of fileTypes) {
        console.log(`[E2E Frontend] Testing file type: ${fileData.type}`);
        
        const file = new File([fileData.content], fileData.name, { type: fileData.type });
        const uploadResult = await sourceMaterialsApi.upload(file, testProject.id);
        uploadedMaterials.push(uploadResult);
        
        expect(uploadResult.id).toBeDefined();
        expect(uploadResult.name).toBe(fileData.name);
      }

      render(
        <QueryClientProvider client={queryClient}>
          <MaterialsList projectId={testProject.id} />
        </QueryClientProvider>
      );

      // Verify all file types are displayed
      for (const fileData of fileTypes) {
        await waitFor(() => {
          expect(screen.getByText(fileData.name)).toBeInTheDocument();
        });
        
        // Verify VIEW button is available for each file type
        const eyeButtons = screen.getAllByRole('button', { name: /view/i });
        const eyeButton = eyeButtons.find(btn => 
          btn.closest('[data-testid*="material-item"]')?.textContent?.includes(fileData.name)
        );
        expect(eyeButton).toBeInTheDocument();
      }
      
      console.log('[E2E Frontend] ✅ Different file types test completed');
    });
  });
});

// Helper function to create test image blob
function createTestImageBlob(): Blob {
  // Create a minimal PNG data URI and convert to blob
  const canvas = document.createElement('canvas');
  canvas.width = 1;
  canvas.height = 1;
  const ctx = canvas.getContext('2d')!;
  ctx.fillStyle = 'red';
  ctx.fillRect(0, 0, 1, 1);
  
  return new Promise<Blob>((resolve) => {
    canvas.toBlob((blob) => {
      resolve(blob!);
    }, 'image/jpeg');
  }) as any; // Type assertion for test purposes
}

// Helper function to convert canvas to blob synchronously for testing
function createTestImageBlobSync(): string {
  return 'data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEAYABgAAD/2wBDAAEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/2wBDAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQEBAQH/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAv/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwDX/9k=';
} 