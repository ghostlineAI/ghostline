'use client';

import { useState, useEffect, useCallback } from 'react';
import Image from 'next/image';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Button } from '@/components/ui/button';
import { Loader2, Download, X } from 'lucide-react';
import { toast } from 'sonner';
import { sourceMaterialsApi } from '@/lib/api/source-materials';
import apiClient from '@/lib/api/client';

interface MaterialPreviewModalProps {
  material: {
    id: string;
    filename: string;
    material_type: string;
    file_size: number;
    mime_type: string;
    s3_url?: string;
  };
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function MaterialPreviewModal({ material, open, onOpenChange }: MaterialPreviewModalProps) {
  const [loading, setLoading] = useState(true);
  const [previewContent, setPreviewContent] = useState<string | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);

  const loadPreview = useCallback(async () => {
    setLoading(true);
    try {
      // For text files, fetch content directly
      if (material.material_type === 'TEXT') {
        const text = await sourceMaterialsApi.getContent(material.id);
        setPreviewContent(text);
      }
      
      // For images and audio, use the proxied content URL to avoid CORS issues
      if (['IMAGE', 'AUDIO'].includes(material.material_type.toUpperCase())) {
        // Fetch the content using the API client (which includes auth headers)
        const response = await apiClient.get(
          `/source-materials/${material.id}/content`,
          { responseType: 'blob' }
        );
        
        // Create a blob URL from the response
        const blob = new Blob([response.data], { type: material.mime_type });
        const objectUrl = URL.createObjectURL(blob);
        setPreviewUrl(objectUrl);
      }
    } catch (error) {
      console.error('Failed to load preview:', error);
      toast.error('Failed to load preview');
    } finally {
      setLoading(false);
    }
  }, [material.id, material.material_type, material.mime_type]);

  useEffect(() => {
    if (open) {
      loadPreview();
    }
    
    // Cleanup function to revoke any object URLs
    return () => {
      if (previewUrl && previewUrl.startsWith('blob:')) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [open, loadPreview]);

  const handleDownload = async () => {
    try {
      console.log('🔽 Starting download for material:', material.id);
      await sourceMaterialsApi.download(material.id);
      toast.success('Download started');
      console.log('✅ Download completed successfully');
    } catch (error) {
      console.error('❌ Download error:', error);
      toast.error('Failed to download file. Please try again.');
    }
  };

  const renderPreview = () => {
    if (loading) {
      return (
        <div className="flex items-center justify-center h-96">
          <Loader2 className="h-8 w-8 animate-spin" />
        </div>
      );
    }

    switch (material.material_type.toUpperCase()) {
      case 'TEXT':
        return (
          <div className="bg-gray-50 rounded-lg p-4 max-h-96 overflow-y-auto">
            <pre className="whitespace-pre-wrap text-sm font-mono">
              {previewContent || 'No content available'}
            </pre>
          </div>
        );

      case 'PDF':
        return (
          <div className="flex flex-col items-center justify-center h-96 bg-gray-50 rounded-lg">
            <p className="text-gray-600 mb-4">PDF preview not available</p>
            <Button onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download PDF
            </Button>
          </div>
        );

      case 'IMAGE':
        return (
          <div className="flex items-center justify-center bg-gray-50 rounded-lg p-4">
            {previewUrl ? (
              <div className="relative w-full h-96">
                <Image
                  src={previewUrl}
                  alt={material.filename}
                  fill
                  className="object-contain"
                />
              </div>
            ) : (
              <p className="text-gray-600">Image not available</p>
            )}
          </div>
        );

      case 'AUDIO':
        return (
          <div className="flex flex-col items-center justify-center h-96 bg-gray-50 rounded-lg p-8">
            {previewUrl ? (
              <audio
                controls
                className="w-full max-w-md"
              >
                <source src={previewUrl} type={material.mime_type} />
                Your browser does not support the audio element.
              </audio>
            ) : (
              <p className="text-gray-600">Audio not available</p>
            )}
          </div>
        );

      case 'DOCX':
        return (
          <div className="flex flex-col items-center justify-center h-96 bg-gray-50 rounded-lg">
            <p className="text-gray-600 mb-4">Word document preview not available</p>
            <Button onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download Document
            </Button>
          </div>
        );

      default:
        return (
          <div className="flex flex-col items-center justify-center h-96 bg-gray-50 rounded-lg">
            <p className="text-gray-600 mb-4">Preview not available for this file type</p>
            <Button onClick={handleDownload}>
              <Download className="h-4 w-4 mr-2" />
              Download File
            </Button>
          </div>
        );
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle className="flex items-center justify-between">
            <span className="truncate mr-4">{material.filename}</span>
            <Button
              variant="ghost"
              size="icon"
              onClick={() => onOpenChange(false)}
            >
              <X className="h-4 w-4" />
            </Button>
          </DialogTitle>
        </DialogHeader>
        <div className="mt-4">
          {renderPreview()}
        </div>
      </DialogContent>
    </Dialog>
  );
} 