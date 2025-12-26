'use client';

import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { BookOpen, CheckCircle, Loader2 } from 'lucide-react';
import { toast } from 'sonner';
import apiClient from '@/lib/api/client';

interface Chapter {
  chapter_number: number;
  title: string;
  status: string;
}

export function GenerationWizard({ projectId }: { projectId: string }) {
  const [isGenerating, setIsGenerating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [chapters, setChapters] = useState<Chapter[]>([]);
  const [completedChapters, setCompletedChapters] = useState(0);

  useEffect(() => {
    // Fetch chapters when component mounts
    fetchChapters();
  }, [projectId]); // eslint-disable-line react-hooks/exhaustive-deps

  const fetchChapters = async () => {
    try {
      const response = await apiClient.get(`/projects/${projectId}/chapters`);
      setChapters(response.data);
      const completed = response.data.filter((ch: Chapter) => ch.status === 'completed').length;
      setCompletedChapters(completed);
      setProgress((completed / response.data.length) * 100);
    } catch (error) {
      console.error('Failed to fetch chapters:', error);
    }
  };

  const startGeneration = async () => {
    setIsGenerating(true);
    try {
      await apiClient.post(`/projects/${projectId}/generate`);
      toast.success('Book generation started!');
      
      // Poll for progress
      const interval = setInterval(async () => {
        await fetchChapters();
      }, 5000);

      // Store interval ID for cleanup
      return () => clearInterval(interval);
    } catch (error) {
      console.error('Failed to start generation:', error);
      toast.error('Failed to start book generation');
      setIsGenerating(false);
    }
  };

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Book Generation</CardTitle>
        </CardHeader>
        <CardContent className="space-y-6">
          {!isGenerating && chapters.length === 0 && (
            <div className="text-center py-8">
              <BookOpen className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
              <p className="text-muted-foreground mb-4">
                Ready to generate your book? Click below to start the AI generation process.
              </p>
              <Button onClick={startGeneration} size="lg">
                Start Generation
              </Button>
            </div>
          )}

          {(isGenerating || chapters.length > 0) && (
            <>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Generation Progress</span>
                  <span>{Math.round(progress)}%</span>
                </div>
                <Progress value={progress} className="h-2" />
              </div>

              <div className="space-y-3">
                {chapters.map((chapter) => (
                  <div
                    key={chapter.chapter_number}
                    className="flex items-center justify-between p-3 rounded-lg border bg-card"
                  >
                    <div className="flex items-center gap-3">
                      <div className="text-sm font-medium">
                        Chapter {chapter.chapter_number}
                      </div>
                      <div className="text-sm text-muted-foreground">
                        {chapter.title}
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      {chapter.status === 'completed' ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : chapter.status === 'generating' ? (
                        <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                      ) : (
                        <div className="h-5 w-5 rounded-full border-2 border-muted" />
                      )}
                    </div>
                  </div>
                ))}
              </div>

              <div className="bg-muted/50 rounded-lg p-4 text-center">
                <p className="text-sm text-muted-foreground">
                  {completedChapters} of {chapters.length} chapters completed
                </p>
              </div>

              {progress === 100 && (
                <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
                  <CheckCircle className="h-8 w-8 text-green-500 mx-auto mb-2" />
                  <p className="text-green-800 font-medium">
                    Book Generation Complete!
                  </p>
                  <p className="text-sm text-green-600 mt-1">
                    All {chapters.length} chapters have been generated
                  </p>
                </div>
              )}
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
} 