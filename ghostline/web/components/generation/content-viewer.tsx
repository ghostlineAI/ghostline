'use client';

import { useState } from 'react';
import { BookOutline, GeneratedChapter } from '@/lib/api/generation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  BookOpen,
  FileText,
  ChevronLeft,
  ChevronRight,
  Download,
  Copy,
  Check,
  BarChart3,
} from 'lucide-react';
import { toast } from 'sonner';

interface ContentViewerProps {
  outline?: BookOutline;
  chapters?: GeneratedChapter[];
  onClose?: () => void;
}

export function ContentViewer({ outline, chapters = [], onClose }: ContentViewerProps) {
  const [selectedChapter, setSelectedChapter] = useState(0);
  const [copied, setCopied] = useState(false);

  const handleCopy = async (content: string) => {
    await navigator.clipboard.writeText(content);
    setCopied(true);
    toast.success('Copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  };

  const handleExport = () => {
    // Create a text file with all content
    let content = '';
    
    if (outline) {
      content += `# ${outline.title}\n\n`;
      content += `${outline.premise}\n\n`;
      content += `## Table of Contents\n\n`;
      outline.chapters?.forEach((ch) => {
        content += `${ch.number}. ${ch.title}\n`;
      });
      content += '\n---\n\n';
    }
    
    chapters.forEach((ch) => {
      content += `# Chapter ${ch.number}: ${ch.title}\n\n`;
      content += `${ch.content}\n\n`;
      content += '---\n\n';
    });

    const blob = new Blob([content], { type: 'text/markdown' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${outline?.title || 'book'}.md`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Book exported!');
  };

  const currentChapter = chapters[selectedChapter];
  const totalWords = chapters.reduce((sum, ch) => sum + (ch.word_count || 0), 0);

  return (
    <div className="space-y-6">
      {/* Header Stats */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{chapters.length}</div>
            <div className="text-sm text-gray-500">Chapters</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">{totalWords.toLocaleString()}</div>
            <div className="text-sm text-gray-500">Total Words</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-2xl font-bold">
              {chapters.length > 0 
                ? (chapters.reduce((sum, ch) => sum + (ch.voice_score || 0), 0) / chapters.length * 100).toFixed(0)
                : 0}%
            </div>
            <div className="text-sm text-gray-500">Avg Voice Match</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4 flex items-center justify-center">
            <Button onClick={handleExport} className="w-full">
              <Download className="h-4 w-4 mr-2" />
              Export Book
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Content Tabs */}
      <Tabs defaultValue="chapters" className="w-full">
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="outline">
            <BookOpen className="h-4 w-4 mr-2" />
            Outline
          </TabsTrigger>
          <TabsTrigger value="chapters">
            <FileText className="h-4 w-4 mr-2" />
            Chapters
          </TabsTrigger>
        </TabsList>

        {/* Outline Tab */}
        <TabsContent value="outline" className="mt-4">
          {outline ? (
            <Card>
              <CardHeader>
                <CardTitle>{outline.title}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <p className="text-gray-600">{outline.premise}</p>
                
                {outline.themes && outline.themes.length > 0 && (
                  <div className="flex gap-2">
                    {outline.themes.map((theme, i) => (
                      <Badge key={i} variant="secondary">{theme}</Badge>
                    ))}
                  </div>
                )}

                <div className="space-y-3 mt-6">
                  {outline.chapters?.map((ch, i) => (
                    <div 
                      key={i} 
                      className="p-4 bg-gray-50 rounded-lg cursor-pointer hover:bg-gray-100"
                      onClick={() => {
                        setSelectedChapter(i);
                        (document.querySelector('[data-value="chapters"]') as HTMLButtonElement)?.click();
                      }}
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-8 h-8 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center font-semibold text-sm">
                          {ch.number}
                        </span>
                        <div>
                          <p className="font-medium">{ch.title}</p>
                          <p className="text-sm text-gray-500">{ch.summary}</p>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-gray-500">
                No outline generated yet
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Chapters Tab */}
        <TabsContent value="chapters" className="mt-4">
          {chapters.length > 0 ? (
            <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
              {/* Chapter List */}
              <div className="lg:col-span-1">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Chapters</CardTitle>
                  </CardHeader>
                  <CardContent className="p-2">
                    <ScrollArea className="h-[400px]">
                      {chapters.map((ch, i) => (
                        <button
                          key={i}
                          onClick={() => setSelectedChapter(i)}
                          className={`w-full p-3 text-left rounded-lg mb-1 transition-colors ${
                            selectedChapter === i 
                              ? 'bg-purple-100 border-purple-300' 
                              : 'hover:bg-gray-100'
                          }`}
                        >
                          <p className="font-medium text-sm">Ch. {ch.number}</p>
                          <p className="text-xs text-gray-500 truncate">{ch.title}</p>
                          <div className="flex gap-2 mt-1">
                            <Badge variant="outline" className="text-xs">
                              {ch.word_count?.toLocaleString()} words
                            </Badge>
                          </div>
                        </button>
                      ))}
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>

              {/* Chapter Content */}
              <div className="lg:col-span-3">
                <Card>
                  <CardHeader className="flex flex-row items-center justify-between">
                    <div>
                      <CardTitle>
                        Chapter {currentChapter?.number}: {currentChapter?.title}
                      </CardTitle>
                      <div className="flex gap-4 mt-2 text-sm text-gray-500">
                        <span>{currentChapter?.word_count?.toLocaleString()} words</span>
                        <span className="flex items-center">
                          <BarChart3 className="h-3 w-3 mr-1" />
                          Voice: {((currentChapter?.voice_score || 0) * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                    <div className="flex gap-2">
                      <Button
                        variant="outline"
                        size="icon"
                        disabled={selectedChapter === 0}
                        onClick={() => setSelectedChapter(prev => prev - 1)}
                      >
                        <ChevronLeft className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        disabled={selectedChapter === chapters.length - 1}
                        onClick={() => setSelectedChapter(prev => prev + 1)}
                      >
                        <ChevronRight className="h-4 w-4" />
                      </Button>
                      <Button
                        variant="outline"
                        size="icon"
                        onClick={() => handleCopy(currentChapter?.content || '')}
                      >
                        {copied ? <Check className="h-4 w-4 text-green-500" /> : <Copy className="h-4 w-4" />}
                      </Button>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <ScrollArea className="h-[500px]">
                      <div className="prose prose-gray max-w-none whitespace-pre-wrap">
                        {currentChapter?.content || 'No content available'}
                      </div>
                    </ScrollArea>
                  </CardContent>
                </Card>
              </div>
            </div>
          ) : (
            <Card>
              <CardContent className="p-8 text-center text-gray-500">
                No chapters generated yet. Start a generation to create content.
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}

