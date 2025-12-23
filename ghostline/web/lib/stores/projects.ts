import { create } from 'zustand';

export interface Project {
  id: string;
  title: string;  // Changed from 'name' to match API
  description?: string;
  genre?: 'fiction' | 'non_fiction' | 'memoir' | 'business' | 'self_help' | 'academic' | 'technical' | 'other';
  status: 'draft' | 'processing' | 'ready' | 'published' | 'archived';
  owner_id?: string;
  user_id?: string;
  forked_from_project_id?: string;
  created_at: string;
  updated_at: string;
  chapter_count?: number;
  word_count?: number;
  target_audience?: string;
  language?: string;
}

interface ProjectState {
  projects: Project[];
  currentProject: Project | null;
  isLoading: boolean;
  error: string | null;
  setProjects: (projects: Project[]) => void;
  setCurrentProject: (project: Project | null) => void;
  addProject: (project: Project) => void;
  updateProject: (id: string, updates: Partial<Project>) => void;
  deleteProject: (id: string) => void;
  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
}

export const useProjectStore = create<ProjectState>((set) => ({
  projects: [],
  currentProject: null,
  isLoading: false,
  error: null,
  
  setProjects: (projects) => set({ projects }),
  
  setCurrentProject: (project) => set({ currentProject: project }),
  
  addProject: (project) => set((state) => ({
    projects: [...state.projects, project],
  })),
  
  updateProject: (id, updates) => set((state) => ({
    projects: state.projects.map((p) => 
      p.id === id ? { ...p, ...updates } : p
    ),
    currentProject: state.currentProject?.id === id 
      ? { ...state.currentProject, ...updates } 
      : state.currentProject,
  })),
  
  deleteProject: (id) => set((state) => ({
    projects: state.projects.filter((p) => p.id !== id),
    currentProject: state.currentProject?.id === id ? null : state.currentProject,
  })),
  
  setLoading: (loading) => set({ isLoading: loading }),
  
  setError: (error) => set({ error }),
})); 