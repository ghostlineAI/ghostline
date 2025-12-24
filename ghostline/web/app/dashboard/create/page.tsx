'use client';

import { useState, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '@/lib/api/projects';
import { generationApi, GenerationTask, isTaskComplete, isTaskPaused, isTaskRunning, TASK_POLL_INTERVAL } from '@/lib/api/generation';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { 
  Sparkles,
  BookOpen,
  FileText,
  Loader2,
  Plus,
  CheckCircle,
  XCircle,
  PauseCircle,
  PlayCircle,
  AlertCircle,
} from 'lucide-react';
import { toast } from 'sonner';
import Link from 'next/link';
import { OutlineReviewModal } from '@/components/generation/outline-review-modal';
import { GenerationProgress } from '@/components/generation/generation-progress';

const statusColors: Record<string, string> = {
  pending: 'bg-gray-100 text-gray-800',
  queued: 'bg-blue-100 text-blue-800',
  running: 'bg-yellow-100 text-yellow-800',
  paused: 'bg-orange-100 text-orange-800',
  completed: 'bg-green-100 text-green-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-gray-100 text-gray-500',
};

const statusIcons = {
  pending: Loader2,
  queued: Loader2,
  running: Loader2,
  paused: PauseCircle,
  completed: CheckCircle,
  failed: XCircle,
  cancelled: XCircle,
};

export default function CreatePage() {
  const queryClient = useQueryClient();
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const [activeTaskId, setActiveTaskId] = useState<string | null>(null);
  const [showOutlineReview, setShowOutlineReview] = useState(false);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  });

  // Get tasks for selected project
  const { data: projectTasks = [], refetch: refetchTasks } = useQuery({
    queryKey: ['project-tasks', selectedProjectId],
    queryFn: () => selectedProjectId ? generationApi.getProjectTasks(selectedProjectId) : Promise.resolve([]),
    enabled: !!selectedProjectId,
  });

  // Poll active task status
  const { data: activeTask } = useQuery({
    queryKey: ['task-status', activeTaskId],
    queryFn: () => activeTaskId ? generationApi.getTaskStatus(activeTaskId) : Promise.resolve(null),
    enabled: !!activeTaskId,
    refetchInterval: (query) => {
      const task = query.state.data;
      if (task && isTaskRunning(task)) {
        return TASK_POLL_INTERVAL;
      }
      return false; // Stop polling when complete
    },
  });

  // Handle task status changes
  useEffect(() => {
    if (activeTask) {
      if (isTaskPaused(activeTask) && activeTask.current_step?.includes('outline')) {
        setShowOutlineReview(true);
      }
      if (isTaskComplete(activeTask)) {
        refetchTasks();
        if (activeTask.status === 'completed') {
          toast.success('Generation completed!');
        } else if (activeTask.status === 'failed') {
          toast.error(`Generation failed: ${activeTask.error_message || 'Unknown error'}`);
        }
      }
    }
  }, [activeTask, refetchTasks]);

  // Start outline generation
  const startOutlineMutation = useMutation({
    mutationFn: (projectId: string) => generationApi.startOutlineGeneration(projectId),
    onSuccess: (response) => {
      setActiveTaskId(response.task_id);
      toast.success('Outline generation started!');
      refetchTasks();
    },
    onError: (error: Error) => {
      toast.error(`Failed to start generation: ${error.message}`);
    },
  });

  // Start full book generation
  const startBookMutation = useMutation({
    mutationFn: (projectId: string) => generationApi.startBookGeneration(projectId),
    onSuccess: (response) => {
      setActiveTaskId(response.task_id);
      toast.success('Book generation started!');
      refetchTasks();
    },
    onError: (error: Error) => {
      toast.error(`Failed to start generation: ${error.message}`);
    },
  });

  // Generate single chapter
  const generateChapterMutation = useMutation({
    mutationFn: ({ projectId, chapterNumber }: { projectId: string; chapterNumber: number }) => 
      generationApi.generateChapter(projectId, chapterNumber),
    onSuccess: (response) => {
      setActiveTaskId(response.task_id);
      toast.success('Chapter generation started!');
      refetchTasks();
    },
    onError: (error: Error) => {
      toast.error(`Failed to start chapter generation: ${error.message}`);
    },
  });

  // Approve outline
  const approveOutlineMutation = useMutation({
    mutationFn: ({ taskId, approve, feedback }: { taskId: string; approve: boolean; feedback?: string }) =>
      generationApi.approveOutline(taskId, { approve, feedback }),
    onSuccess: (response) => {
      setShowOutlineReview(false);
      toast.success(response.approved ? 'Outline approved! Continuing generation...' : 'Feedback submitted');
      // Continue polling
      queryClient.invalidateQueries({ queryKey: ['task-status', activeTaskId] });
    },
    onError: (error: Error) => {
      toast.error(`Failed to process outline: ${error.message}`);
    },
  });

  const activeProjects = projects.filter(p => 
    p.status === 'processing' || p.status === 'draft' || p.status === 'ready'
  );

  // Find the most recent active/paused task
  const currentTask = projectTasks.find(t => isTaskRunning(t) || isTaskPaused(t)) || 
                      (activeTask && (isTaskRunning(activeTask) || isTaskPaused(activeTask)) ? activeTask : null);

  const isGenerating = startOutlineMutation.isPending || 
                       startBookMutation.isPending || 
                       generateChapterMutation.isPending ||
                       (currentTask && isTaskRunning(currentTask));

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Create Content</h1>
        <p className="mt-1 text-gray-600">
          Use AI to generate outlines, chapters, and complete manuscripts
        </p>
      </div>

      {/* Project Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Select Project</CardTitle>
          <CardDescription>Choose a project to work on</CardDescription>
        </CardHeader>
        <CardContent>
          {projects.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4">No projects found. Create a project first.</p>
              <Link href="/dashboard/projects/new">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Project
                </Button>
              </Link>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => {
                    setSelectedProjectId(project.id);
                    setActiveTaskId(null);
                  }}
                  className={`p-4 border rounded-lg text-left transition-all hover:shadow-md ${
                    selectedProjectId === project.id 
                      ? 'border-purple-500 bg-purple-50' 
                      : 'hover:border-purple-300'
                  }`}
                >
                  <h3 className="font-medium">{project.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{project.genre}</p>
                  <div className="mt-3 flex items-center text-xs text-gray-500">
                    <FileText className="h-3 w-3 mr-1" />
                    <span className="capitalize">{project.status}</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Active Task Progress */}
      {currentTask && (
        <GenerationProgress 
          task={currentTask} 
          onApproveOutline={() => setShowOutlineReview(true)}
        />
      )}

      {/* Generation Options */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="flex items-center justify-between">
              <BookOpen className="h-8 w-8 text-purple-500" />
              <Sparkles className="h-5 w-5 text-yellow-500" />
            </div>
            <CardTitle className="mt-4">Generate Outline</CardTitle>
            <CardDescription>
              Create a structured outline for your book based on your source materials
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              className="w-full" 
              disabled={!selectedProjectId || !!isGenerating}
              onClick={() => selectedProjectId && startOutlineMutation.mutate(selectedProjectId)}
            >
              {startOutlineMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                'Start Outline Generation'
              )}
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="flex items-center justify-between">
              <FileText className="h-8 w-8 text-blue-500" />
              <Sparkles className="h-5 w-5 text-yellow-500" />
            </div>
            <CardTitle className="mt-4">Write Chapter</CardTitle>
            <CardDescription>
              Generate individual chapters with AI assistance and your voice
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              className="w-full" 
              disabled={!selectedProjectId || !!isGenerating}
              onClick={() => selectedProjectId && generateChapterMutation.mutate({ 
                projectId: selectedProjectId, 
                chapterNumber: 1 
              })}
            >
              {generateChapterMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                'Generate Chapter'
              )}
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="flex items-center justify-between">
              <BookOpen className="h-8 w-8 text-green-500" />
              <Sparkles className="h-5 w-5 text-yellow-500" />
            </div>
            <CardTitle className="mt-4">Full Generation</CardTitle>
            <CardDescription>
              Generate a complete manuscript from start to finish
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              className="w-full" 
              disabled={!selectedProjectId || !!isGenerating}
              onClick={() => selectedProjectId && startBookMutation.mutate(selectedProjectId)}
            >
              {startBookMutation.isPending ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Starting...
                </>
              ) : (
                'Generate Full Book'
              )}
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Recent Tasks */}
      {selectedProjectId && projectTasks.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Generation Tasks</CardTitle>
            <CardDescription>View the history of generation tasks for this project</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {projectTasks.slice(0, 5).map((task) => {
                const StatusIcon = statusIcons[task.status] || AlertCircle;
                return (
                  <div 
                    key={task.id} 
                    className="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div className="flex items-center space-x-3">
                      <StatusIcon className={`h-5 w-5 ${
                        task.status === 'completed' ? 'text-green-500' :
                        task.status === 'failed' ? 'text-red-500' :
                        task.status === 'running' ? 'text-yellow-500 animate-spin' :
                        task.status === 'paused' ? 'text-orange-500' :
                        'text-gray-400'
                      }`} />
                      <div>
                        <p className="font-medium text-sm capitalize">
                          {task.task_type.replace('_', ' ')}
                        </p>
                        <p className="text-xs text-gray-500">{task.current_step}</p>
                      </div>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Badge className={statusColors[task.status]}>
                        {task.status}
                      </Badge>
                      {task.progress > 0 && task.progress < 100 && (
                        <span className="text-sm text-gray-500">{task.progress}%</span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Outline Review Modal */}
      {showOutlineReview && activeTask && (
        <OutlineReviewModal
          isOpen={showOutlineReview}
          onClose={() => setShowOutlineReview(false)}
          outline={activeTask.output_data?.outline}
          onApprove={(feedback) => {
            approveOutlineMutation.mutate({
              taskId: activeTask.id,
              approve: true,
              feedback,
            });
          }}
          onReject={(feedback) => {
            approveOutlineMutation.mutate({
              taskId: activeTask.id,
              approve: false,
              feedback,
            });
          }}
          isLoading={approveOutlineMutation.isPending}
        />
      )}
    </div>
  );
}
