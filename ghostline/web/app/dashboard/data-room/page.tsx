'use client';

import { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '@/lib/api/projects';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { FileUpload } from '@/components/data-room/file-upload';
import { MaterialsList } from '@/components/data-room/materials-list';
import { 
  FileText, 
  Image, 
  Mic, 
  Plus
} from 'lucide-react';

export default function DataRoomPage() {
  const [selectedProjectId, setSelectedProjectId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  });

  const handleUploadComplete = () => {
    // Invalidate the materials list to refresh it
    queryClient.invalidateQueries({ queryKey: ['source-materials', selectedProjectId] });
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Data Room</h1>
        <p className="mt-1 text-gray-600">
          Upload and manage source materials for your book projects
        </p>
      </div>

      {/* Project Selector */}
      <Card>
        <CardHeader>
          <CardTitle>Select Project</CardTitle>
          <CardDescription>Choose a project to upload materials to</CardDescription>
        </CardHeader>
        <CardContent>
          {projects.length === 0 ? (
            <div className="text-center py-8">
              <p className="text-gray-500 mb-4">No projects found. Create a project first.</p>
              <Button>
                <Plus className="h-4 w-4 mr-2" />
                Create Project
              </Button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {projects.map((project) => (
                <button
                  key={project.id}
                  onClick={() => setSelectedProjectId(project.id)}
                  className={`p-4 border rounded-lg text-left transition-colors ${
                    selectedProjectId === project.id
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <h3 className="font-medium">{project.title}</h3>
                  <p className="text-sm text-gray-600 mt-1">{project.genre}</p>
                </button>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Upload Section */}
      {selectedProjectId && (
        <>
          <Card>
            <CardHeader>
              <CardTitle>Upload Materials</CardTitle>
              <CardDescription>
                Add documents, images, audio recordings, and notes to your project
              </CardDescription>
            </CardHeader>
            <CardContent>
              <FileUpload 
                projectId={selectedProjectId} 
                onUploadComplete={handleUploadComplete}
              />
            </CardContent>
          </Card>

          {/* Materials List */}
          <Card>
            <CardContent className="pt-6">
              <MaterialsList projectId={selectedProjectId} />
            </CardContent>
          </Card>
        </>
      )}

      {/* Material Types */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-3">
            <FileText className="h-8 w-8 text-blue-500 mb-2" />
            <CardTitle className="text-lg">Documents</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600">PDF, DOCX, TXT files</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            {/* eslint-disable-next-line jsx-a11y/alt-text */}
            <Image className="h-8 w-8 text-green-500 mb-2" />
            <CardTitle className="text-lg">Images</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600">JPG, PNG, GIF files</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <Mic className="h-8 w-8 text-purple-500 mb-2" />
            <CardTitle className="text-lg">Audio</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-gray-600">MP3, WAV, M4A files</p>
          </CardContent>
        </Card>
      </div>
    </div>
  );
} 