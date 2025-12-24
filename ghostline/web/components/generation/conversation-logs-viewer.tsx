'use client';

import { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  MessageSquare,
  User,
  Bot,
  ArrowRight,
  Clock,
  Coins,
  Hash,
  ChevronDown,
  ChevronUp,
  RefreshCw,
  Download,
} from 'lucide-react';

export interface ConversationMessage {
  timestamp: string;
  role: 'user' | 'assistant' | 'agent' | 'system';
  agent: string;
  content: string;
  full_content_length?: number;
  tokens?: number;
  cost?: string;
  duration_ms?: number;
  model?: string;
  from?: string;
  to?: string;
  structured?: Record<string, unknown>;
}

export interface ConversationSession {
  session_id: string;
  workflow_type: string;
  started_at: string;
  ended_at?: string;
  status: 'running' | 'completed' | 'failed' | 'interrupted';
  error?: string;
  stats: {
    total_tokens: number;
    total_cost: string;
    total_duration_ms: number;
    total_duration_sec: number;
    message_count: number;
    agent_calls: Record<string, number>;
  };
  messages: ConversationMessage[];
}

interface ConversationLogsViewerProps {
  session?: ConversationSession;
  onRefresh?: () => void;
  isLoading?: boolean;
}

const roleIcons = {
  user: User,
  assistant: Bot,
  agent: ArrowRight,
  system: MessageSquare,
};

const roleColors = {
  user: 'bg-blue-100 text-blue-700 border-blue-200',
  assistant: 'bg-green-100 text-green-700 border-green-200',
  agent: 'bg-purple-100 text-purple-700 border-purple-200',
  system: 'bg-gray-100 text-gray-700 border-gray-200',
};

export function ConversationLogsViewer({ session, onRefresh, isLoading }: ConversationLogsViewerProps) {
  const [expandedMessages, setExpandedMessages] = useState<Set<number>>(new Set());

  const toggleMessage = (index: number) => {
    const newExpanded = new Set(expandedMessages);
    if (newExpanded.has(index)) {
      newExpanded.delete(index);
    } else {
      newExpanded.add(index);
    }
    setExpandedMessages(newExpanded);
  };

  const handleDownload = () => {
    if (!session) return;
    const blob = new Blob([JSON.stringify(session, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `conversation-${session.session_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (!session) {
    return (
      <Card>
        <CardContent className="p-8 text-center text-gray-500">
          <MessageSquare className="h-12 w-12 mx-auto mb-4 text-gray-300" />
          <p>No conversation logs available</p>
          <p className="text-sm mt-2">Run a generation task to see the agent conversations</p>
        </CardContent>
      </Card>
    );
  }

  const statusColors = {
    running: 'bg-yellow-100 text-yellow-700',
    completed: 'bg-green-100 text-green-700',
    failed: 'bg-red-100 text-red-700',
    interrupted: 'bg-orange-100 text-orange-700',
  };

  return (
    <div className="space-y-4">
      {/* Session Header */}
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="flex items-center gap-2">
                <MessageSquare className="h-5 w-5 text-purple-500" />
                Agent Conversation Log
              </CardTitle>
              <CardDescription className="mt-1">
                Session: {session.session_id}
              </CardDescription>
            </div>
            <div className="flex gap-2">
              {onRefresh && (
                <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading}>
                  <RefreshCw className={`h-4 w-4 mr-2 ${isLoading ? 'animate-spin' : ''}`} />
                  Refresh
                </Button>
              )}
              <Button variant="outline" size="sm" onClick={handleDownload}>
                <Download className="h-4 w-4 mr-2" />
                Export
              </Button>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          {/* Stats Row */}
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-4">
            <div className="flex items-center gap-2">
              <Badge className={statusColors[session.status]}>
                {session.status}
              </Badge>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Hash className="h-4 w-4" />
              <span>{session.stats.total_tokens.toLocaleString()} tokens</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Coins className="h-4 w-4" />
              <span>{session.stats.total_cost}</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <Clock className="h-4 w-4" />
              <span>{session.stats.total_duration_sec.toFixed(1)}s</span>
            </div>
            <div className="flex items-center gap-2 text-sm text-gray-600">
              <MessageSquare className="h-4 w-4" />
              <span>{session.stats.message_count} messages</span>
            </div>
          </div>

          {/* Agent Call Counts */}
          <div className="flex flex-wrap gap-2">
            {Object.entries(session.stats.agent_calls).map(([agent, count]) => (
              <Badge key={agent} variant="outline" className="text-xs">
                {agent}: {count}
              </Badge>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Messages */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg">Conversation Flow</CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          <ScrollArea className="h-[500px]">
            <div className="space-y-1 p-4">
              {session.messages.map((msg, index) => {
                const RoleIcon = roleIcons[msg.role] || MessageSquare;
                const isExpanded = expandedMessages.has(index);
                const isLong = (msg.full_content_length || msg.content.length) > 200;
                
                return (
                  <div 
                    key={index}
                    className={`p-3 rounded-lg border ${roleColors[msg.role]}`}
                  >
                    {/* Header */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2">
                        <RoleIcon className="h-4 w-4" />
                        <span className="font-medium text-sm">{msg.agent}</span>
                        {msg.role === 'agent' && msg.from && msg.to && (
                          <span className="text-xs">
                            {msg.from} → {msg.to}
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-3 text-xs">
                        {msg.tokens && (
                          <span className="flex items-center gap-1">
                            <Hash className="h-3 w-3" />
                            {msg.tokens}
                          </span>
                        )}
                        {msg.cost && (
                          <span className="flex items-center gap-1">
                            <Coins className="h-3 w-3" />
                            {msg.cost}
                          </span>
                        )}
                        {msg.duration_ms && (
                          <span className="flex items-center gap-1">
                            <Clock className="h-3 w-3" />
                            {(msg.duration_ms / 1000).toFixed(1)}s
                          </span>
                        )}
                        {msg.model && (
                          <Badge variant="outline" className="text-xs py-0">
                            {msg.model.split('/').pop()?.split('-').slice(0, 2).join('-')}
                          </Badge>
                        )}
                      </div>
                    </div>

                    {/* Content */}
                    <div className="text-sm whitespace-pre-wrap break-words">
                      {isLong && !isExpanded 
                        ? msg.content.slice(0, 200) + '...'
                        : msg.content
                      }
                    </div>

                    {/* Expand/Collapse */}
                    {isLong && (
                      <button
                        onClick={() => toggleMessage(index)}
                        className="flex items-center gap-1 text-xs mt-2 hover:underline"
                      >
                        {isExpanded ? (
                          <>
                            <ChevronUp className="h-3 w-3" />
                            Show less
                          </>
                        ) : (
                          <>
                            <ChevronDown className="h-3 w-3" />
                            Show full ({msg.full_content_length || msg.content.length} chars)
                          </>
                        )}
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </ScrollArea>
        </CardContent>
      </Card>

      {/* Error Display */}
      {session.error && (
        <Card className="border-red-200 bg-red-50">
          <CardContent className="p-4">
            <p className="text-red-700 text-sm">{session.error}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}


