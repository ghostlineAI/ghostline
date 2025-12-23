'use client';

import { useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { useProjectStore } from '@/lib/stores/projects';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ArrowLeft,
  FileText,
  BookOpen,
  Upload,
  Edit,
  Download,
  BarChart,
  Globe,
  Users,
} from 'lucide-react';
import { format } from 'date-fns';

const statusColors = {
  draft: 'bg-gray-100 text-gray-800',
  processing: 'bg-blue-100 text-blue-800',
  ready: 'bg-green-100 text-green-800',
  published: 'bg-purple-100 text-purple-800',
  archived: 'bg-red-100 text-red-800',
};

const genreLabels = {
  fiction: 'Fiction',
  non_fiction: 'Non-Fiction',
  memoir: 'Memoir',
  business: 'Business',
  self_help: 'Self-Help',
  academic: 'Academic',
  technical: 'Technical',
  other: 'Other',
};

export default function ProjectDetailPage() {
  const router = useRouter();
  const { currentProject } = useProjectStore();

  useEffect(() => {
    // If no project is selected, redirect to projects list
    if (!currentProject) {
      router.push('/dashboard/projects');
    }
  }, [currentProject, router]);

  if (!currentProject) {
    return null; // Will redirect
  }

  return (
    <div className="p-6 max-w-7xl mx-auto">
      {/* Back Button */}
      <Link 
        href="/dashboard/projects"
        className="inline-flex items-center text-gray-600 hover:text-gray-900 mb-6"
      >
        <ArrowLeft className="h-4 w-4 mr-2" />
        Back to Projects
      </Link>

      {/* Project Header */}
      <div className="mb-8">
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">{currentProject.title}</h1>
            <p className="mt-2 text-lg text-gray-600">{currentProject.description}</p>
          </div>
          <Badge className={statusColors[currentProject.status]}>
            {currentProject.status.replace('_', ' ')}
          </Badge>
        </div>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8">
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Genre</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{genreLabels[currentProject.genre || 'other']}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Chapters</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">{currentProject.chapter_count || 0}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Word Count</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {currentProject.word_count ? currentProject.word_count.toLocaleString() : '0'}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium text-gray-600">Created</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-2xl font-bold">
              {format(new Date(currentProject.created_at), 'MMM d')}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Action Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {/* Data Room */}
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardHeader>
            <Upload className="h-8 w-8 text-blue-500 mb-2" />
            <CardTitle>Data Room</CardTitle>
            <CardDescription>Upload and manage source materials</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/dashboard/data-room">
              <Button className="w-full">
                <Upload className="h-4 w-4 mr-2" />
                Manage Materials
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Create/Edit */}
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardHeader>
            <Edit className="h-8 w-8 text-green-500 mb-2" />
            <CardTitle>Create Content</CardTitle>
            <CardDescription>Write and edit your book</CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/dashboard/create">
              <Button className="w-full">
                <Edit className="h-4 w-4 mr-2" />
                Start Writing
              </Button>
            </Link>
          </CardContent>
        </Card>

        {/* Analytics */}
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardHeader>
            <BarChart className="h-8 w-8 text-purple-500 mb-2" />
            <CardTitle>Analytics</CardTitle>
            <CardDescription>Track progress and insights</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" variant="outline" disabled>
              <BarChart className="h-4 w-4 mr-2" />
              View Analytics
            </Button>
          </CardContent>
        </Card>

        {/* Export */}
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardHeader>
            <Download className="h-8 w-8 text-orange-500 mb-2" />
            <CardTitle>Export</CardTitle>
            <CardDescription>Download your book</CardDescription>
          </CardHeader>
          <CardContent>
            <Button 
              className="w-full" 
              variant="outline" 
              disabled={currentProject.status !== 'ready' && currentProject.status !== 'published'}
            >
              <Download className="h-4 w-4 mr-2" />
              Export Book
            </Button>
          </CardContent>
        </Card>

        {/* Chapters */}
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardHeader>
            <BookOpen className="h-8 w-8 text-indigo-500 mb-2" />
            <CardTitle>Chapters</CardTitle>
            <CardDescription>View and organize chapters</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" variant="outline">
              <BookOpen className="h-4 w-4 mr-2" />
              Manage Chapters
            </Button>
          </CardContent>
        </Card>

        {/* Settings */}
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <CardHeader>
            <FileText className="h-8 w-8 text-gray-500 mb-2" />
            <CardTitle>Project Settings</CardTitle>
            <CardDescription>Configure project details</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full" variant="outline">
              <FileText className="h-4 w-4 mr-2" />
              Settings
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Additional Details */}
      {(currentProject.target_audience || currentProject.language) && (
        <Card className="mt-8">
          <CardHeader>
            <CardTitle>Additional Information</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {currentProject.target_audience && (
              <div className="flex items-center gap-2">
                <Users className="h-5 w-5 text-gray-500" />
                <span className="font-medium">Target Audience:</span>
                <span className="text-gray-600">{currentProject.target_audience}</span>
              </div>
            )}
            {currentProject.language && (
              <div className="flex items-center gap-2">
                <Globe className="h-5 w-5 text-gray-500" />
                <span className="font-medium">Language:</span>
                <span className="text-gray-600">{currentProject.language.toUpperCase()}</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
} 