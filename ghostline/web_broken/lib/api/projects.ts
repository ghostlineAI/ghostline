import apiClient from './client';

export interface Project {
  id: string;
  title: string;
  description?: string;
  genre: string;
  status: string;
  created_at: string;
  updated_at: string;
  user_id: string;
  chapter_count?: number;
  word_count?: number;
}

export interface CreateProjectData {
  title: string;
  description?: string;
  genre: string;
}

export interface UpdateProjectData {
  title?: string;
  description?: string;
  status?: string;
}

export const projectsApi = {
  /**
   * List all projects for the current user.
   */
  async list(): Promise<Project[]> {
    const response = await apiClient.get('/projects/');
    return response.data;
  },

  /**
   * Get a specific project by ID.
   */
  async get(id: string): Promise<Project> {
    const response = await apiClient.get(`/projects/${id}`);
    return response.data;
  },

  /**
   * Create a new project.
   */
  async create(data: CreateProjectData): Promise<Project> {
    const response = await apiClient.post('/projects/', data);
    return response.data;
  },

  /**
   * Update an existing project.
   */
  async update(id: string, data: UpdateProjectData): Promise<Project> {
    const response = await apiClient.patch(`/projects/${id}`, data);
    return response.data;
  },

  /**
   * Delete a project.
   */
  async delete(id: string): Promise<void> {
    await apiClient.delete(`/projects/${id}`);
  },

  /**
   * Fork (duplicate) a project.
   */
  async fork(id: string): Promise<Project> {
    const response = await apiClient.post(`/projects/${id}/fork`);
    return response.data;
  },

  /**
   * Get source materials for a project.
   */
  async getSourceMaterials(projectId: string): Promise<unknown[]> {
    const response = await apiClient.get(`/projects/${projectId}/source-materials`);
    return response.data;
  },

  /**
   * Get chapters for a project.
   */
  async getChapters(projectId: string): Promise<unknown[]> {
    const response = await apiClient.get(`/projects/${projectId}/chapters`);
    return response.data;
  },

  /**
   * Get project outline.
   */
  async getOutline(projectId: string): Promise<unknown> {
    const response = await apiClient.get(`/projects/${projectId}/outline`);
    return response.data;
  },
};
