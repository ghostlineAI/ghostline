'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { sourceMaterialsApi } from '@/lib/api/source-materials';
import { FileText, Image, Mic, Trash2, Eye, Download, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { formatDistanceToNow } from 'date-fns';
import { 
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { MaterialPreviewModal } from './material-preview-modal';

interface MaterialsListProps {
  projectId: string;
}

interface SourceMaterial {
  id: string;
  filename: string;
  material_type: string;
  file_size: number;
  mime_type: string;
  processing_status: string;
  created_at: string;
  s3_url?: string;
}

export function MaterialsList({ projectId }: MaterialsListProps) {
  const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);
  const [selectedMaterial, setSelectedMaterial] = useState<SourceMaterial | null>(null);
  const [previewMaterial, setPreviewMaterial] = useState<SourceMaterial | null>(null);
  const queryClient = useQueryClient();

  // Fetch materials
  const { data: materials = [], isLoading, error } = useQuery({
    queryKey: ['source-materials', projectId],
    queryFn: () => sourceMaterialsApi.list(projectId),
    enabled: !!projectId,
  });

  // Delete mutation
  const deleteMutation = useMutation({
    mutationFn: (materialId: string) => {
      console.log('🗑️ Starting delete API call for material:', materialId);
      return sourceMaterialsApi.delete(materialId);
    },
    onSuccess: () => {
      console.log('✅ Delete API call successful');
      queryClient.invalidateQueries({ queryKey: ['source-materials', projectId] });
      toast.success('Material deleted successfully');
      setDeleteDialogOpen(false);
      setSelectedMaterial(null);
    },
    onError: (error) => {
      console.error('❌ Delete API call failed:', error);
      if (error instanceof Error) {
        if (error.message.includes('401') || error.message.includes('403')) {
          toast.error('Authentication required. Please refresh the page and try again.');
        } else if (error.message.includes('404')) {
          toast.error('File not found. It may have already been deleted.');
        } else {
          toast.error(`Delete failed: ${error.message}`);
        }
      } else {
        toast.error('Failed to delete material');
      }
    },
  });

  const getFileIcon = (materialType: string) => {
    switch (materialType.toUpperCase()) {
      case 'TEXT':
      case 'PDF':
      case 'DOCX':
        return <FileText className="h-5 w-5" aria-label="Document file" />;
      case 'IMAGE':
        return <Image className="h-5 w-5" aria-label="Image file" />;
      case 'AUDIO':
        return <Mic className="h-5 w-5" aria-label="Audio file" />;
      default:
        return <FileText className="h-5 w-5" aria-label="File" />;
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getStatusBadgeVariant = (status: string) => {
    switch (status.toUpperCase()) {
      case 'COMPLETED':
        return 'default';
      case 'PROCESSING':
      case 'PENDING':
        return 'secondary';
      case 'FAILED':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-6 w-6 animate-spin" />
      </div>
    );
  }

  if (error) {
    return (
      <Card className="p-6">
        <p className="text-sm text-red-600">Failed to load materials</p>
      </Card>
    );
  }

  if (materials.length === 0) {
    return (
      <Card className="p-6">
        <p className="text-sm text-gray-500 text-center">
          No materials uploaded yet. Start by uploading some files above.
        </p>
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-2">
        <h3 className="text-lg font-semibold mb-4">Uploaded Materials</h3>
        <div className="divide-y divide-gray-200 rounded-lg border">
          {materials.map((material) => (
            <div
              key={material.id}
              className="flex items-center justify-between p-4 hover:bg-gray-50 transition-colors"
            >
              <div className="flex items-center space-x-3 flex-1">
                <div className="flex-shrink-0">
                  {getFileIcon(material.material_type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-gray-900 truncate">
                    {material.filename}
                  </p>
                  <div className="flex items-center space-x-2 mt-1">
                    <span className="text-xs text-gray-500">
                      {formatFileSize(material.file_size)}
                    </span>
                    <span className="text-xs text-gray-400">•</span>
                    <span className="text-xs text-gray-500">
                      {formatDistanceToNow(new Date(material.created_at), { addSuffix: true })}
                    </span>
                    <Badge variant={getStatusBadgeVariant(material.processing_status)}>
                      {material.processing_status}
                    </Badge>
                  </div>
                </div>
              </div>
              <div className="flex items-center space-x-2 ml-4">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    console.log('👁️ View button clicked for material:', material.id, material.filename);
                    if (material.processing_status !== 'COMPLETED') {
                      toast.info('File is still processing. Preview will be available once processing is complete.');
                      return;
                    }
                    setPreviewMaterial(material);
                    console.log('✅ Opening preview modal for:', material.filename);
                  }}
                  disabled={material.processing_status !== 'COMPLETED'}
                  title={material.processing_status !== 'COMPLETED' ? 'File is still processing' : 'Preview file'}
                >
                  <Eye className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={async () => {
                    console.log('🔽 Download button clicked for material:', material.id);
                    if (material.processing_status !== 'COMPLETED') {
                      toast.info('File is still processing. Download will be available once processing is complete.');
                      return;
                    }
                    
                    try {
                      // Use the new download() method that forces file download
                      await sourceMaterialsApi.download(material.id);
                      console.log('✅ Download initiated for:', material.filename);
                      toast.success('Download started');
                    } catch (error) {
                      console.error('❌ Download failed:', error);
                      toast.error('Failed to download file. Please try again.');
                    }
                  }}
                  disabled={material.processing_status !== 'COMPLETED'}
                  title={material.processing_status !== 'COMPLETED' ? 'File is still processing' : 'Download file'}
                >
                  <Download className="h-4 w-4" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    console.log('🗑️ Delete button clicked for material:', material.id, material.filename);
                    setSelectedMaterial(material);
                    setDeleteDialogOpen(true);
                    console.log('✅ Opening delete confirmation dialog');
                  }}
                  className="hover:text-red-600"
                  title="Delete file"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Delete Confirmation Dialog */}
      <AlertDialog open={deleteDialogOpen} onOpenChange={setDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete Material</AlertDialogTitle>
            <AlertDialogDescription>
              Are you sure you want to delete &ldquo;{selectedMaterial?.filename}&rdquo;? This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (selectedMaterial) {
                  deleteMutation.mutate(selectedMaterial.id);
                }
              }}
              className="bg-red-600 hover:bg-red-700"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {/* Preview Modal */}
      {previewMaterial && (
        <MaterialPreviewModal
          material={previewMaterial}
          open={!!previewMaterial}
          onOpenChange={(open) => {
            if (!open) setPreviewMaterial(null);
          }}
        />
      )}
    </>
  );
} 