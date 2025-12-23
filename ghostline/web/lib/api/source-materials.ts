import apiClient from './client';

interface UploadResponse {
  id: string;
  name: string;
  type: string;
  size: number;
  status: string;
  message?: string;
  duplicate?: boolean;
}

interface SourceMaterial {
  id: string;
  filename: string;
  material_type: string;
  file_size: number;
  mime_type: string;
  processing_status: string;
  created_at: string;
  s3_url?: string;
}

export const sourceMaterialsApi = {
  async upload(file: File, projectId: string): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('project_id', projectId);

    const response = await apiClient.post<UploadResponse>(
      '/source-materials/upload',
      formData,
      {
        headers: {
          'Content-Type': undefined, // Let axios set the boundary automatically
        },
      }
    );

    return response.data;
  },

  async list(projectId: string): Promise<SourceMaterial[]> {
    const response = await apiClient.get<SourceMaterial[]>(
      `/projects/${projectId}/source-materials`
    );
    return response.data;
  },

  async get(materialId: string): Promise<SourceMaterial> {
    const response = await apiClient.get<SourceMaterial>(
      `/source-materials/${materialId}`
    );
    return response.data;
  },

  async delete(materialId: string): Promise<void> {
    await apiClient.delete(`/source-materials/${materialId}`);
  },

  async getDownloadUrl(materialId: string): Promise<{ download_url: string; filename: string; expires_in: number }> {
    const response = await apiClient.get<{ download_url: string; filename: string; expires_in: number }>(
      `/source-materials/${materialId}/download-url`
    );
    return response.data;
  },

  async getContent(materialId: string): Promise<string> {
    // Use the new /content endpoint that proxies the request server-side to avoid CORS
    const response = await apiClient.get(
      `/source-materials/${materialId}/content`,
      {
        responseType: 'text',
      }
    );
    return response.data;
  },

  async download(materialId: string): Promise<void> {
    // Use the new /download endpoint that forces file download
    const response = await apiClient.get(
      `/source-materials/${materialId}/download`,
      {
        responseType: 'blob',
      }
    );

    // Get filename from Content-Disposition header or fallback
    const contentDisposition = response.headers['content-disposition'];
    let filename = 'download';
    if (contentDisposition) {
      const filenameMatch = contentDisposition.match(/filename="([^"]+)"/);
      if (filenameMatch) {
        filename = filenameMatch[1];
      }
    }

    // Create download link
    const blob = new Blob([response.data]);
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    window.URL.revokeObjectURL(url);
  },
}; 