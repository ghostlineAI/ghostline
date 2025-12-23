'use client';

import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { projectsApi } from '@/lib/api/projects';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { 
  Sparkles,
  BookOpen,
  FileText,
  Loader2,
  Plus
} from 'lucide-react';

export default function CreatePage() {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  });

  const activeProjects = projects.filter(p => 
    p.status === 'processing' || p.status === 'draft' || p.status === 'ready'
  );

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
          {activeProjects.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4">No active projects found. Create a project first.</p>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Project
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {activeProjects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => {
                    setSelectedProjectId(project.id);
                  }}
                  className="p-4 border rounded-lg text-left transition-all hover:shadow-md hover:border-purple-300"
                >
                  <h3 className="font-medium">{project.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{project.genre}</p>
                  <div className="mt-3 flex items-center text-xs text-gray-500">
                    <FileText className="h-3 w-3 mr-1" />
                    <span>In Progress</span>
                  </div>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

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
            <Button className="w-full" disabled={!selectedProjectId}>
              Start Outline Generation
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
            <Button className="w-full" disabled={!selectedProjectId}>
              Generate Chapter
            </Button>
          </CardContent>
        </Card>

        <Card className="hover:shadow-lg transition-shadow">
          <CardHeader>
            <div className="flex items-center justify-between">
              <Loader2 className="h-8 w-8 text-green-500" />
              <Sparkles className="h-5 w-5 text-yellow-500" />
            </div>
            <CardTitle className="mt-4">Full Generation</CardTitle>
            <CardDescription>
              Generate a complete manuscript from start to finish
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" disabled={!selectedProjectId}>
              Generate Full Book
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Quick Prompt */}
      {selectedProjectId && (
        <Card>
          <CardHeader>
            <CardTitle>Quick Generation</CardTitle>
            <CardDescription>
              Describe what you want to create and let AI handle the rest
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              placeholder="Example: Write a humorous autobiography based on my uploaded materials, focusing on my career transition from engineering to comedy..."
              className="min-h-[120px] mb-4"
            />
            <Button>
              <Sparkles className="h-4 w-4 mr-2" />
              Generate Content
            </Button>
          </CardContent>
        </Card>
      )}
    </div>
  );
} 