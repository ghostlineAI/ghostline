/**
 * Real E2E test for file upload functionality - NO MOCKS
 * Tests against live API
 */

import { sourceMaterialsApi } from '@/lib/api/source-materials';
import { authApi } from '@/lib/api/auth';
import { projectsApi } from '@/lib/api/projects';
import { useAuthStore } from '@/lib/stores/auth';

// Skip these tests in CI environment as they require real API access
// and Jest/JSDOM has CORS restrictions
const describeSkipInCI = process.env.CI ? describe.skip : describe;

describeSkipInCI('File Upload E2E Tests', () => {
  const timestamp = Date.now();
  const testUser = {
    email: `file_upload_test_${timestamp}@example.com`,
    password: 'TestPass123!',
    username: `fileuploadtest_${timestamp}`,
    full_name: 'File Upload Test User'
  };
  
  let authToken: string;
  let testProject: any;

  beforeAll(async () => {
    // Register test user
    try {
      await authApi.register(testUser);
    } catch (error) {
      console.log('User might already exist');
    }

    // Login
    const loginResponse = await authApi.login({
      email: testUser.email,
      password: testUser.password
    });
    
    authToken = loginResponse.access_token;
    // Note: setAuth is called automatically inside authApi.login()

    // Create test project
    testProject = await projectsApi.create({
      title: `Upload Test Project ${timestamp}`,
      genre: 'fiction',
      description: 'Testing file uploads'
    });
  });

  afterAll(async () => {
    // Cleanup
    useAuthStore.getState().logout();
  });

  it('should upload a text file successfully', async () => {
    // Create a test file
    const content = 'This is test content for file upload';
    const file = new File([content], 'test-document.txt', { type: 'text/plain' });

    // Upload file
    const response = await sourceMaterialsApi.upload(file, testProject.id);

    expect(response).toBeDefined();
    expect(response.id).toBeDefined();
    expect(response.name).toBe('test-document.txt');
    expect(response.type).toBe('txt');
    expect(response.size).toBe(content.length);
    expect(response.status).toBe('processing');
  });

  it('should handle duplicate file uploads', async () => {
    // Create file with same name
    const file = new File(['duplicate content'], 'duplicate-test.txt', { type: 'text/plain' });

    // First upload
    const firstUpload = await sourceMaterialsApi.upload(file, testProject.id);
    expect(firstUpload.duplicate).toBeFalsy();

    // Second upload with same filename
    const secondUpload = await sourceMaterialsApi.upload(file, testProject.id);
    expect(secondUpload.duplicate).toBe(true);
    expect(secondUpload.message).toContain('already exists');
  });

  it('should reject invalid file types', async () => {
    const file = new File(['fake exe'], 'malware.exe', { type: 'application/x-executable' });

    await expect(sourceMaterialsApi.upload(file, testProject.id))
      .rejects
      .toThrow();
  });

  it('should reject files over size limit', async () => {
    // Create 51MB file (over 50MB limit)
    const largeContent = new Array(51 * 1024 * 1024).fill('x').join('');
    const file = new File([largeContent], 'large-file.txt', { type: 'text/plain' });

    await expect(sourceMaterialsApi.upload(file, testProject.id))
      .rejects
      .toThrow();
  });

  it('should list uploaded materials', async () => {
    // Upload a file first
    const file = new File(['list test'], 'list-test.txt', { type: 'text/plain' });
    await sourceMaterialsApi.upload(file, testProject.id);

    // List materials
    const materials = await sourceMaterialsApi.list(testProject.id);
    
    expect(Array.isArray(materials)).toBe(true);
    expect(materials.length).toBeGreaterThan(0);
    
    const uploaded = materials.find(m => m.filename === 'list-test.txt');
    expect(uploaded).toBeDefined();
  });

  it('should upload PDF files', async () => {
    // Create minimal PDF content
    const pdfContent = `%PDF-1.4
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /Resources << >> /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
trailer
<< /Size 4 /Root 1 0 R >>
startxref
217
%%EOF`;

    const file = new File([pdfContent], 'test.pdf', { type: 'application/pdf' });
    
    const response = await sourceMaterialsApi.upload(file, testProject.id);
    
    expect(response.type).toBe('pdf');
    expect(response.name).toBe('test.pdf');
  });

  it('should upload image files', async () => {
    // Create minimal PNG (1x1 pixel transparent)
    const pngData = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==', 'base64');
    const file = new File([pngData], 'test.png', { type: 'image/png' });
    
    const response = await sourceMaterialsApi.upload(file, testProject.id);
    
    expect(response.type).toBe('png');
    expect(response.name).toBe('test.png');
  });

  it('should handle concurrent uploads', async () => {
    const files = [
      new File(['content1'], 'concurrent1.txt', { type: 'text/plain' }),
      new File(['content2'], 'concurrent2.txt', { type: 'text/plain' }),
      new File(['content3'], 'concurrent3.txt', { type: 'text/plain' })
    ];

    // Upload all files concurrently
    const uploads = await Promise.all(
      files.map(file => sourceMaterialsApi.upload(file, testProject.id))
    );

    expect(uploads).toHaveLength(3);
    uploads.forEach((upload, index) => {
      expect(upload.name).toBe(`concurrent${index + 1}.txt`);
      expect(upload.status).toBe('processing');
    });
  });
}); 