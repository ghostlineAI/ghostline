'use client';

import React from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { useAuthStore } from '@/lib/stores/auth';
import { useProjectStore, type Project } from '@/lib/stores/projects';
import { projectsApi } from '@/lib/api/projects';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { 
  BookOpen, 
  FileText, 
  PenTool, 

  Plus,
  ArrowRight,
  Coins
} from 'lucide-react';

export default function DashboardPage() {
  const user = useAuthStore((state) => state.user);
  const router = useRouter();
  const { setCurrentProject } = useProjectStore();

  const { data: projects = [] } = useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  });

  const handleOpenProject = (project: Project) => {
    setCurrentProject(project);
    router.push('/dashboard/project-detail');
  };

  const stats = {
    totalProjects: projects.length,
    activeProjects: projects.filter(p => p.status === 'draft' || p.status === 'processing').length,
    completedProjects: projects.filter(p => p.status === 'ready' || p.status === 'published').length,
    tokenBalance: user?.token_balance || 0,
  };

  return (
    <div className="p-6 space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">
            Welcome back, {user?.full_name || user?.username || 'Author'}!
          </h1>
          <p className="mt-1 text-gray-600">
            Here&apos;s an overview of your ghostwriting projects
          </p>
        </div>
        <Link href="/dashboard/projects/new">
          <Button className="mt-4 sm:mt-0">
            <Plus className="h-4 w-4 mr-2" />
            New Project
          </Button>
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Total Projects</CardTitle>
            <BookOpen className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.totalProjects}</div>
            <p className="text-xs text-muted-foreground">
              All your book projects
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Active Projects</CardTitle>
            <PenTool className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.activeProjects}</div>
            <p className="text-xs text-muted-foreground">
              Currently in progress
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Completed</CardTitle>
            <FileText className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.completedProjects}</div>
            <p className="text-xs text-muted-foreground">
              Ready for publishing
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-sm font-medium">Token Balance</CardTitle>
            <Coins className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{stats.tokenBalance.toLocaleString()}</div>
            <p className="text-xs text-muted-foreground">
              Available for generation
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <Link href="/dashboard/projects/new">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Start New Book
                <ArrowRight className="h-5 w-5" />
              </CardTitle>
              <CardDescription>
                Begin a new ghostwriting project with AI assistance
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <Link href="/dashboard/data-room">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Upload Materials
                <ArrowRight className="h-5 w-5" />
              </CardTitle>
              <CardDescription>
                Add source documents, notes, and recordings
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>

        <Card className="hover:shadow-lg transition-shadow cursor-pointer">
          <Link href="/dashboard/create">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                Continue Writing
                <ArrowRight className="h-5 w-5" />
              </CardTitle>
              <CardDescription>
                Resume work on your active projects
              </CardDescription>
            </CardHeader>
          </Link>
        </Card>
      </div>

      {/* Recent Projects */}
      {projects.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Recent Projects</CardTitle>
            <CardDescription>Your latest book projects</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {projects.slice(0, 5).map((project) => (
                <button
                  key={project.id}
                  onClick={() => handleOpenProject(project)}
                  className="flex items-center justify-between p-4 rounded-lg border hover:bg-gray-50 transition-colors w-full text-left"
                >
                  <div>
                    <h3 className="font-medium">{project.title}</h3>
                    <p className="text-sm text-gray-600">
                      {project.genre} • {project.status.replace('_', ' ').toLowerCase()}
                    </p>
                  </div>
                  <ArrowRight className="h-5 w-5 text-gray-400" />
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
} 