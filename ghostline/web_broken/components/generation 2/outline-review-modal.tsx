'use client';

import { useState } from 'react';
import { BookOutline, ChapterOutline } from '@/lib/api/generation';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  BookOpen,
  Check,
  X,
  MessageSquare,
  ChevronDown,
  ChevronUp,
  Loader2,
  Target,
  Users,
  Lightbulb,
} from 'lucide-react';

interface OutlineReviewModalProps {
  isOpen: boolean;
  onClose: () => void;
  outline?: BookOutline;
  onApprove: (feedback?: string) => void;
  onReject: (feedback: string) => void;
  isLoading?: boolean;
}

export function OutlineReviewModal({
  isOpen,
  onClose,
  outline,
  onApprove,
  onReject,
  isLoading = false,
}: OutlineReviewModalProps) {
  const [feedback, setFeedback] = useState('');
  const [expandedChapters, setExpandedChapters] = useState<Set<number>>(new Set([0]));
  const [showFeedbackInput, setShowFeedbackInput] = useState(false);

  const toggleChapter = (index: number) => {
    const newExpanded = new Set(expandedChapters);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedChapters(newExpanded);
  };

  const handleApprove = () => {
    onApprove(feedback || undefined);
    setFeedback('');
    setShowFeedbackInput(false);
  };

  const handleReject = () => {
    if (!feedback.trim()) {
      setShowFeedbackInput(true);
      return;
    }
    onReject(feedback);
    setFeedback('');
    setShowFeedbackInput(false);
  };

  if (!outline) {
    return (
      <Dialog open={isOpen} onOpenChange={onClose}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Outline Review</DialogTitle>
          </DialogHeader>
          <div className="py-8 text-center text-gray-500">
            <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
            <p>Loading outline...</p>
          </div>
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-4xl max-h-[90vh]">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-purple-500" />
            Review Generated Outline
          </DialogTitle>
          <DialogDescription>
            Review the AI-generated outline and approve to continue, or provide feedback for changes.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="h-[60vh] pr-4">
          <div className="space-y-6">
            {/* Book Title & Premise */}
            <div className="space-y-3">
              <h2 className="text-2xl font-bold text-gray-900">{outline.title}</h2>
              <p className="text-gray-600 leading-relaxed">{outline.premise}</p>
            </div>

            {/* Metadata */}
            <div className="flex flex-wrap gap-4">
              {outline.target_audience && (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Users className="h-4 w-4 text-blue-500" />
                  <span>{outline.target_audience}</span>
                </div>
              )}
              {outline.themes && outline.themes.length > 0 && (
                <div className="flex items-center gap-2">
                  <Lightbulb className="h-4 w-4 text-yellow-500" />
                  <div className="flex gap-1">
                    {outline.themes.map((theme, i) => (
                      <Badge key={i} variant="secondary" className="text-xs">
                        {theme}
                      </Badge>
                    ))}
                  </div>
                </div>
              )}
            </div>

            {/* Chapters */}
            <div className="space-y-3">
              <h3 className="font-semibold text-lg flex items-center gap-2">
                <Target className="h-5 w-5 text-purple-500" />
                Chapters ({outline.chapters?.length || 0})
              </h3>
              
              <div className="space-y-2">
                {outline.chapters?.map((chapter, index) => (
                  <div 
                    key={index}
                    className="border rounded-lg overflow-hidden"
                  >
                    <button
                      onClick={() => toggleChapter(index)}
                      className="w-full p-4 flex items-center justify-between bg-gray-50 hover:bg-gray-100 transition-colors text-left"
                    >
                      <div className="flex items-center gap-3">
                        <span className="w-8 h-8 rounded-full bg-purple-100 text-purple-600 flex items-center justify-center font-semibold text-sm">
                          {chapter.number}
                        </span>
                        <span className="font-medium">{chapter.title}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {chapter.estimated_words && (
                          <span className="text-xs text-gray-500">
                            ~{chapter.estimated_words.toLocaleString()} words
                          </span>
                        )}
                        {expandedChapters.has(index) ? (
                          <ChevronUp className="h-4 w-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="h-4 w-4 text-gray-400" />
                        )}
                      </div>
                    </button>
                    
                    {expandedChapters.has(index) && (
                      <div className="p-4 border-t bg-white space-y-3">
                        <p className="text-gray-600 text-sm">{chapter.summary}</p>
                        {chapter.key_points && chapter.key_points.length > 0 && (
                          <div className="space-y-1">
                            <p className="text-xs font-medium text-gray-500 uppercase">Key Points</p>
                            <ul className="list-disc list-inside text-sm text-gray-600 space-y-1">
                              {chapter.key_points.map((point, i) => (
                                <li key={i}>{point}</li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>

            {/* Feedback Input */}
            {showFeedbackInput && (
              <div className="space-y-2 pt-4 border-t">
                <label className="text-sm font-medium text-gray-700">
                  Provide feedback (required for rejection)
                </label>
                <Textarea
                  value={feedback}
                  onChange={(e) => setFeedback(e.target.value)}
                  placeholder="Describe what changes you'd like to see in the outline..."
                  rows={4}
                />
              </div>
            )}
          </div>
        </ScrollArea>

        <DialogFooter className="flex-col sm:flex-row gap-2 pt-4 border-t">
          <Button
            variant="outline"
            onClick={() => setShowFeedbackInput(!showFeedbackInput)}
            className="sm:mr-auto"
          >
            <MessageSquare className="h-4 w-4 mr-2" />
            {showFeedbackInput ? 'Hide Feedback' : 'Add Feedback'}
          </Button>
          
          <div className="flex gap-2">
            <Button
              variant="destructive"
              onClick={handleReject}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <X className="h-4 w-4 mr-2" />
              )}
              Request Changes
            </Button>
            <Button
              onClick={handleApprove}
              disabled={isLoading}
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                <Check className="h-4 w-4 mr-2" />
              )}
              Approve & Continue
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}



