/**
 * Generation API client
 * 
 * Handles all AI generation endpoints:
 * - Start generation (outline, chapter, full book)
 * - Poll task status
 * - Approve outline
 * - Submit feedback
 * - Resume paused tasks
 */

import apiClient from './client';

export interface GenerationTask {
  id: string;
  project_id: string;
  task_type: 'outline_generation' | 'chapter_generation' | 'voice_analysis' | 'embedding';
  status: 'pending' | 'queued' | 'running' | 'paused' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  current_step: string;
  agent_name: string;
  token_usage?: number;
  estimated_cost?: number;
  error_message?: string;
  output_data?: {
    outline?: BookOutline;
    chapters?: GeneratedChapter[];
    voice_profile?: VoiceProfile;
    feedback_history?: FeedbackEntry[];
    conversation_log?: string;
  };
  created_at: string;
  started_at?: string;
  completed_at?: string;
}

export interface BookOutline {
  title: string;
  premise: string;
  chapters: ChapterOutline[];
  themes: string[];
  target_audience: string;
}

export interface ChapterOutline {
  number: number;
  title: string;
  summary: string;
  key_points: string[];
  estimated_words: number;
}

export interface GeneratedChapter {
  number: number;
  title: string;
  content: string;
  word_count: number;
  voice_score: number;
  fact_score: number;
  cohesion_score: number;
}

export interface VoiceProfile {
  style: string;
  tone: string;
  vocabulary_level: string;
  characteristics: string[];
}

export interface FeedbackEntry {
  text: string;
  target: 'outline' | 'chapter' | 'general';
  chapter_number?: number;
  timestamp: string;
}

export interface StartGenerationResponse {
  message: string;
  task_id: string;
  status: string;
  progress?: number;
  current_step?: string;
}

export interface OutlineApprovalRequest {
  approve: boolean;
  feedback?: string;
}

export interface FeedbackRequest {
  feedback: string;
  target: 'outline' | 'chapter' | 'general';
  chapter_number?: number;
}

/**
 * Generation API functions
 */
export const generationApi = {
  /**
   * Start full book generation
   */
  startBookGeneration: async (projectId: string): Promise<StartGenerationResponse> => {
    const response = await apiClient.post(`/generation/${projectId}/generate`);
    return response.data;
  },

  /**
   * Start outline generation only
   */
  startOutlineGeneration: async (projectId: string): Promise<StartGenerationResponse> => {
    const response = await apiClient.post(`/generation/${projectId}/outline`);
    return response.data;
  },

  /**
   * Generate a single chapter
   */
  generateChapter: async (projectId: string, chapterNumber: number): Promise<StartGenerationResponse> => {
    const response = await apiClient.post(`/generation/${projectId}/chapter/${chapterNumber}`);
    return response.data;
  },

  /**
   * Start voice analysis
   */
  analyzeVoice: async (projectId: string): Promise<StartGenerationResponse> => {
    const response = await apiClient.post(`/generation/${projectId}/analyze-voice`);
    return response.data;
  },

  /**
   * Get all tasks for a project
   */
  getProjectTasks: async (projectId: string): Promise<GenerationTask[]> => {
    const response = await apiClient.get(`/generation/${projectId}/tasks`);
    return response.data;
  },

  /**
   * Get a specific task's status
   */
  getTaskStatus: async (taskId: string): Promise<GenerationTask> => {
    const response = await apiClient.get(`/generation/tasks/${taskId}`);
    return response.data;
  },

  /**
   * Approve or reject an outline
   */
  approveOutline: async (taskId: string, request: OutlineApprovalRequest): Promise<{ message: string; task_id: string; approved: boolean }> => {
    const response = await apiClient.post(`/generation/tasks/${taskId}/approve-outline`, request);
    return response.data;
  },

  /**
   * Submit feedback on generated content
   */
  submitFeedback: async (taskId: string, request: FeedbackRequest): Promise<{ message: string; task_id: string }> => {
    const response = await apiClient.post(`/generation/tasks/${taskId}/feedback`, request);
    return response.data;
  },

  /**
   * Resume a paused task
   */
  resumeTask: async (taskId: string): Promise<{ message: string; task_id: string }> => {
    const response = await apiClient.post(`/generation/tasks/${taskId}/resume`);
    return response.data;
  },
};

/**
 * Hook for polling task status
 * 
 * Usage:
 * const { data, isLoading, error } = useTaskPolling(taskId, {
 *   enabled: shouldPoll,
 *   refetchInterval: 2000, // Poll every 2 seconds
 * });
 */
export const TASK_POLL_INTERVAL = 2000; // 2 seconds

export const isTaskComplete = (task: GenerationTask): boolean => {
  return ['completed', 'failed', 'cancelled'].includes(task.status);
};

export const isTaskPaused = (task: GenerationTask): boolean => {
  return task.status === 'paused';
};

export const isTaskRunning = (task: GenerationTask): boolean => {
  return ['pending', 'queued', 'running'].includes(task.status);
};

/**
 * Get conversation logs for a task
 */
export interface ConversationLogMessage {
  timestamp: string;
  role: 'user' | 'assistant' | 'agent' | 'system';
  agent: string;
  content: string;
  full_content_length?: number;
  tokens?: number;
  cost?: string;
  duration_ms?: number;
  model?: string;
  from?: string;
  to?: string;
}

export interface ConversationLogSession {
  session_id: string;
  workflow_type: string;
  started_at?: string;
  ended_at?: string;
  status: string;
  error?: string;
  stats: {
    total_tokens: number;
    total_cost: string;
    total_duration_ms: number;
    total_duration_sec: number;
    message_count: number;
    agent_calls: Record<string, number>;
  };
  messages: ConversationLogMessage[];
}

export const conversationLogsApi = {
  /**
   * Get conversation logs for a task
   */
  getTaskLogs: async (taskId: string): Promise<ConversationLogSession> => {
    const response = await apiClient.get(`/generation/tasks/${taskId}/conversation-logs`);
    return response.data;
  },
};

