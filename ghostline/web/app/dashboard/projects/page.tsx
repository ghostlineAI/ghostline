'use client';

import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '@/lib/api/projects';
import { useProjectStore, type Project } from '@/lib/stores/projects';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import {
  Plus,
  Search,
  MoreVertical,
  Edit,
  Copy,
  Trash,
  BookOpen,
  Calendar,
} from 'lucide-react';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { toast } from 'sonner';
import { format } from 'date-fns';

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  processing: 'bg-blue-100 text-blue-800',
  ready: 'bg-purple-100 text-purple-800',
  published: 'bg-green-100 text-green-800',
  archived: 'bg-gray-100 text-gray-600',
};

const genreLabels = {
  fiction: 'Fiction',
  non_fiction: 'Non-Fiction',
  memoir: 'Biography/Memoir',
  business: 'Business',
  self_help: 'Self-Help',
  academic: 'Academic',
  technical: 'Technical',
  other: 'Other',
};

export default function ProjectsPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const queryClient = useQueryClient();
  const router = useRouter();
  const { setCurrentProject } = useProjectStore();

  const { data: projects = [], isLoading } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  });

  const deleteMutation = useMutation({
    mutationFn: projectsApi.delete,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success('Project deleted successfully');
    },
    onError: () => {
      toast.error('Failed to delete project');
    },
  });

  const forkMutation = useMutation({
    mutationFn: projectsApi.fork,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
      toast.success('Project forked successfully');
    },
    onError: () => {
      toast.error('Failed to fork project');
    },
  });

  const filteredProjects = projects.filter((project) =>
          project.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleDelete = async (id: string) => {
    if (confirm('Are you sure you want to delete this project?')) {
      await deleteMutation.mutateAsync(id);
    }
  };

  const handleFork = async (id: string) => {
    await forkMutation.mutateAsync(id);
  };

  const handleOpenProject = (project: Project) => {
    setCurrentProject(project);
    router.push('/dashboard/project-detail');
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Projects</h1>
          <p className="mt-1 text-gray-600">
            Manage your book projects and track their progress
          </p>
        </div>
        <Link href="/dashboard/projects/new">
          <Button>
            <Plus className="h-4 w-4 mr-2" />
            New Project
          </Button>
        </Link>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          type="text"
          placeholder="Search projects..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Projects Grid */}
      {isLoading ? (
        <div className="text-center py-12">
          <p className="text-gray-500">Loading projects...</p>
        </div>
      ) : filteredProjects.length === 0 ? (
        <Card>
          <CardContent className="text-center py-12">
            <BookOpen className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              {searchQuery ? 'No projects found' : 'No projects yet'}
            </h3>
            <p className="text-gray-500 mb-4">
              {searchQuery
                ? 'Try adjusting your search query'
                : 'Get started by creating your first book project'}
            </p>
            {!searchQuery && (
              <Link href="/dashboard/projects/new">
                <Button>
                  <Plus className="h-4 w-4 mr-2" />
                  Create Project
                </Button>
              </Link>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredProjects.map((project) => (
            <Card key={project.id} className="hover:shadow-lg transition-shadow">
              <CardHeader>
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <CardTitle className="line-clamp-1">{project.title}</CardTitle>
                    <CardDescription className="flex items-center gap-2 mt-1">
                      <span>{project.genre ? genreLabels[project.genre] : 'Unknown'}</span>
                      <span className="text-xs">•</span>
                      <span className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        {format(new Date(project.created_at), 'MMM d, yyyy')}
                      </span>
                    </CardDescription>
                  </div>
                  <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                      <Button variant="ghost" size="icon">
                        <MoreVertical className="h-4 w-4" />
                      </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                      <DropdownMenuItem onClick={() => handleOpenProject(project)}>
                        <Edit className="h-4 w-4 mr-2" />
                        Edit Project
                      </DropdownMenuItem>
                      <DropdownMenuItem onClick={() => handleFork(project.id)}>
                        <Copy className="h-4 w-4 mr-2" />
                        Fork Project
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                      <DropdownMenuItem
                        onClick={() => handleDelete(project.id)}
                        className="text-red-600"
                      >
                        <Trash className="h-4 w-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                    </DropdownMenuContent>
                  </DropdownMenu>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {project.description && (
                    <p className="text-sm text-gray-600 line-clamp-2">
                      {project.description}
                    </p>
                  )}
                  <div className="flex items-center justify-between">
                    <Badge className={project.status ? statusColors[project.status] : 'bg-gray-100 text-gray-800'}>
                      {project.status.replace('_', ' ')}
                    </Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleOpenProject(project)}
                    >
                      Open
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
} 