'use client';

import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, File, X, CheckCircle, AlertCircle, Edit2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { sourceMaterialsApi } from '@/lib/api/source-materials';
import { toast } from 'sonner';
import { isAxiosError } from '@/types/api';

interface FileUploadProps {
  projectId: string;
  onUploadComplete?: () => void;
}

interface FileMetadata {
  title?: string;
  description?: string;
}

interface UploadingFile {
  file: File;
  progress: number;
  status: 'uploading' | 'completed' | 'error' | 'pending_metadata';
  error?: string;
  materialId?: string;
  metadata?: FileMetadata;
}

export function FileUpload({ projectId, onUploadComplete }: FileUploadProps) {
  const [uploadingFiles, setUploadingFiles] = useState<Map<string, UploadingFile>>(new Map());

  const uploadFile = useCallback(async (file: File) => {
    const fileId = `${file.name}-${Date.now()}`;
    
    // Add file to uploading state
    setUploadingFiles((prev) => new Map(prev).set(fileId, {
      file,
      progress: 0,
      status: 'uploading',
    }));

    try {
      // Simulate progress while uploading (since we can't track real upload progress easily)
      const progressInterval = setInterval(() => {
        setUploadingFiles((prev) => {
          const updated = new Map(prev);
          const current = updated.get(fileId);
          if (current && current.status === 'uploading' && current.progress < 90) {
            updated.set(fileId, { ...current, progress: current.progress + 10 });
          }
          return updated;
        });
      }, 200);

      // Upload to API
      const response = await sourceMaterialsApi.upload(file, projectId);
      
      clearInterval(progressInterval);

      if (response.duplicate) {
        // Handle duplicate file
        setUploadingFiles((prev) => {
          const updated = new Map(prev);
          updated.set(fileId, { 
            file, 
            progress: 100, 
            status: 'completed',
            materialId: response.id
          });
          return updated;
        });
        toast.info(response.message || 'This file already exists');
      } else {
        // Mark as completed
        setUploadingFiles((prev) => {
          const updated = new Map(prev);
          updated.set(fileId, { 
            file, 
            progress: 100, 
            status: 'completed',
            materialId: response.id
          });
          return updated;
        });
        toast.success(`${file.name} uploaded successfully`);
      }

      // Remove after delay
      setTimeout(() => {
        setUploadingFiles((prev) => {
          const updated = new Map(prev);
          updated.delete(fileId);
          return updated;
        });
      }, 3000);

      onUploadComplete?.();
    } catch (error) {
      console.error('Upload error:', error);
      
      // Mark as error
      let errorMessage = 'Failed to upload file';
      if (isAxiosError(error) && error.response?.data?.detail) {
        errorMessage = error.response.data.detail;
      }
      
      setUploadingFiles((prev) => {
        const updated = new Map(prev);
        updated.set(fileId, { 
          file, 
          progress: 0, 
          status: 'error',
          error: errorMessage
        });
        return updated;
      });
      
      toast.error(errorMessage);
    }
  }, [projectId, onUploadComplete]);

  const onDrop = useCallback((acceptedFiles: File[]) => {
    acceptedFiles.forEach(uploadFile);
  }, [uploadFile]);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
      'text/plain': ['.txt'],
      'audio/*': ['.mp3', '.wav', '.m4a'],
      'image/*': ['.jpg', '.jpeg', '.png', '.gif'],
    },
    maxSize: 50 * 1024 * 1024, // 50MB
  });

  const removeFile = (fileId: string) => {
    setUploadingFiles((prev) => {
      const updated = new Map(prev);
      updated.delete(fileId);
      return updated;
    });
  };

  const retryUpload = (fileId: string, file: File) => {
    removeFile(fileId);
    uploadFile(file);
  };

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`relative rounded-lg border-2 border-dashed p-8 text-center transition-colors ${
          isDragActive
            ? 'border-blue-500 bg-blue-50'
            : 'border-gray-300 hover:border-gray-400'
        }`}
      >
        <input {...getInputProps()} />
        <Upload className="mx-auto h-12 w-12 text-gray-400" />
        <p className="mt-2 text-sm text-gray-600">
          {isDragActive
            ? 'Drop the files here...'
            : 'Drag and drop files here, or click to select'}
        </p>
        <p className="mt-1 text-xs text-gray-500">
          PDF, DOCX, TXT, Audio files (MP3, WAV), Images (JPG, PNG)
        </p>
        <p className="mt-1 text-xs text-gray-500">Max file size: 50MB</p>
      </div>

      {uploadingFiles.size > 0 && (
        <div className="space-y-2">
          {Array.from(uploadingFiles.entries()).map(([fileId, uploadingFile]) => (
            <div
              key={fileId}
              className="flex items-center space-x-3 rounded-lg border bg-white p-3"
            >
              <File className="h-5 w-5 flex-shrink-0 text-gray-400" />
              <div className="flex-1 space-y-1">
                <p className="text-sm font-medium text-gray-900">
                  {uploadingFile.file.name}
                </p>
                {uploadingFile.status === 'uploading' && (
                  <Progress value={uploadingFile.progress} className="h-1" />
                )}
                {uploadingFile.status === 'error' && uploadingFile.error && (
                  <p className="text-xs text-red-600">{uploadingFile.error}</p>
                )}
              </div>
              <div className="flex-shrink-0">
                {uploadingFile.status === 'uploading' && (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-gray-300 border-t-blue-600" />
                )}
                {uploadingFile.status === 'completed' && (
                  <CheckCircle className="h-5 w-5 text-green-500" />
                )}
                {uploadingFile.status === 'error' && (
                  <AlertCircle className="h-5 w-5 text-red-500" />
                )}
              </div>
              {uploadingFile.status === 'error' && (
                <div className="flex space-x-1">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => retryUpload(fileId, uploadingFile.file)}
                  >
                    Retry
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => removeFile(fileId)}
                  >
                    <X className="h-4 w-4" />
                  </Button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
} 