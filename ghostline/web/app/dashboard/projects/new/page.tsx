'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '@/lib/api/projects';
import { useProjectStore } from '@/lib/stores/projects';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { toast } from 'sonner';
import { ArrowLeft } from 'lucide-react';
import Link from 'next/link';
import { ApiError, isCorsError, isAxiosError } from '@/types/api';

const GENRES = [
  { value: 'fiction', label: 'Fiction' },
  { value: 'non_fiction', label: 'Non-Fiction' },
  { value: 'memoir', label: 'Biography/Memoir' },
  { value: 'technical', label: 'Technical' },
  { value: 'self_help', label: 'Self-Help' },
  { value: 'business', label: 'Business' },
  { value: 'academic', label: 'Academic' },
  { value: 'other', label: 'Other' },
] as const;

export default function NewProjectPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { setCurrentProject } = useProjectStore();
  const [formData, setFormData] = useState({
    title: '',
    description: '',
    genre: '',
  });

  const createProjectMutation = useMutation({
    mutationFn: projectsApi.create,
    onSuccess: async (newProject) => {
      toast.success('Project created successfully!');
      // Set the current project for immediate access
      setCurrentProject(newProject);
      // Invalidate the projects list cache to ensure it refreshes
      await queryClient.invalidateQueries({ queryKey: ['projects'] });
      // Navigate to the project detail page
      router.push('/dashboard/project-detail');
    },
    onError: (error: ApiError) => {
      console.error('Project creation error:', error);
      
      // Check if it's a CORS error from our client interceptor
      if (isCorsError(error)) {
        toast.error('Server error: The backend may not be fully deployed yet. Please try again in a few minutes.');
      } else if (isAxiosError(error) && error.response?.status === 500) {
        toast.error('Server error: Please check if all required fields are filled correctly.');
      } else if (isAxiosError(error) && error.response?.status === 401) {
        toast.error('Authentication error: Please log in again.');
        router.push('/auth/login');
      } else if (isAxiosError(error) && error.response?.data?.detail) {
        toast.error(error.response.data.detail);
      } else {
        toast.error('Failed to create project');
      }
    },
  });

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.title || !formData.genre) {
      toast.error('Please fill in all required fields');
      return;
    }
    createProjectMutation.mutate({
      title: formData.title,
      description: formData.description,
      genre: formData.genre as 'fiction' | 'non_fiction' | 'memoir' | 'business' | 'self_help' | 'academic' | 'technical' | 'other',
    });
  };

  return (
    <div className="p-6 max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-6">
        <Link href="/dashboard/projects" className="flex items-center text-gray-600 hover:text-gray-900 mb-4">
          <ArrowLeft className="h-4 w-4 mr-2" />
          Back to Projects
        </Link>
        <h1 className="text-3xl font-bold text-gray-900">Create New Project</h1>
        <p className="mt-1 text-gray-600">
          Start a new book project with AI assistance
        </p>
      </div>

      <form onSubmit={handleSubmit}>
        <Card>
          <CardHeader>
            <CardTitle>Project Details</CardTitle>
            <CardDescription>
              Provide basic information about your book project
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-6">
            <div className="space-y-2">
              <Label htmlFor="title">Project Title *</Label>
              <Input
                id="title"
                value={formData.title}
                onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                placeholder="My Amazing Book"
                required
              />
            </div>

            <div className="space-y-2">
              <Label htmlFor="genre">Genre *</Label>
              <select
                id="genre"
                value={formData.genre}
                onChange={(e) => setFormData({ ...formData, genre: e.target.value })}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-purple-500"
                required
              >
                <option value="">Select a genre</option>
                {GENRES.map((genre) => (
                  <option key={genre.value} value={genre.value}>
                    {genre.label}
                  </option>
                ))}
              </select>
            </div>

            <div className="space-y-2">
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                value={formData.description}
                onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                placeholder="A brief description of your book project..."
                rows={4}
              />
            </div>

            <div className="flex justify-end space-x-4">
              <Button
                type="button"
                variant="outline"
                onClick={() => router.push('/dashboard/projects')}
              >
                Cancel
              </Button>
              <Button
                type="submit"
                disabled={createProjectMutation.isPending}
              >
                {createProjectMutation.isPending ? 'Creating...' : 'Create Project'}
              </Button>
            </div>
          </CardContent>
        </Card>
      </form>
    </div>
  );
} 