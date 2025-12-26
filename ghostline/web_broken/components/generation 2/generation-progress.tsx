'use client';

import { GenerationTask, isTaskPaused, isTaskRunning } from '@/lib/api/generation';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import {
  Loader2,
  CheckCircle,
  XCircle,
  PauseCircle,
  PlayCircle,
  Eye,
  Sparkles,
} from 'lucide-react';

interface GenerationProgressProps {
  task: GenerationTask;
  onApproveOutline?: () => void;
  onViewContent?: () => void;
}

const statusConfig = {
  pending: { icon: Loader2, color: 'text-gray-400', bg: 'bg-gray-100', label: 'Pending' },
  queued: { icon: Loader2, color: 'text-blue-500', bg: 'bg-blue-100', label: 'Queued' },
  running: { icon: Loader2, color: 'text-yellow-500', bg: 'bg-yellow-100', label: 'Running' },
  paused: { icon: PauseCircle, color: 'text-orange-500', bg: 'bg-orange-100', label: 'Awaiting Input' },
  completed: { icon: CheckCircle, color: 'text-green-500', bg: 'bg-green-100', label: 'Completed' },
  failed: { icon: XCircle, color: 'text-red-500', bg: 'bg-red-100', label: 'Failed' },
  cancelled: { icon: XCircle, color: 'text-gray-400', bg: 'bg-gray-100', label: 'Cancelled' },
};

export function GenerationProgress({ task, onApproveOutline, onViewContent }: GenerationProgressProps) {
  const config = statusConfig[task.status] || statusConfig.pending;
  const StatusIcon = config.icon;
  const isActive = isTaskRunning(task);
  const isPaused = isTaskPaused(task);
  const needsOutlineApproval = isPaused && task.current_step?.toLowerCase().includes('outline');

  return (
    <Card className="border-2 border-purple-200 bg-gradient-to-r from-purple-50 to-indigo-50">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-purple-500" />
            AI Generation in Progress
          </CardTitle>
          <Badge className={`${config.bg} ${config.color}`}>
            <StatusIcon className={`h-3 w-3 mr-1 ${isActive ? 'animate-spin' : ''}`} />
            {config.label}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="text-gray-600">{task.current_step}</span>
            <span className="text-purple-600 font-medium">{task.progress}%</span>
          </div>
          <Progress value={task.progress} className="h-2" />
        </div>

        {/* Agent Info */}
        <div className="flex items-center gap-4 text-sm text-gray-500">
          <span>Agent: <span className="font-medium capitalize">{task.agent_name.replace('_', ' ')}</span></span>
          {task.token_usage && (
            <span>Tokens: <span className="font-medium">{task.token_usage.toLocaleString()}</span></span>
          )}
          {task.estimated_cost && (
            <span>Cost: <span className="font-medium">${task.estimated_cost.toFixed(4)}</span></span>
          )}
        </div>

        {/* Actions */}
        {needsOutlineApproval && onApproveOutline && (
          <div className="pt-2 flex gap-3">
            <Button onClick={onApproveOutline} className="flex-1">
              <Eye className="h-4 w-4 mr-2" />
              Review Outline
            </Button>
          </div>
        )}

        {task.status === 'completed' && task.output_data && onViewContent && (
          <div className="pt-2">
            <Button onClick={onViewContent} variant="outline" className="w-full">
              <Eye className="h-4 w-4 mr-2" />
              View Generated Content
            </Button>
          </div>
        )}

        {task.status === 'failed' && task.error_message && (
          <div className="p-3 bg-red-50 rounded-lg border border-red-200">
            <p className="text-sm text-red-700">{task.error_message}</p>
          </div>
        )}
      </CardContent>
    </Card>
  );
}



