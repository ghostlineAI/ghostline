'use client';

import { useState } from 'react';
import { X } from 'lucide-react';

export function DevelopmentBanner() {
  const [isVisible, setIsVisible] = useState(true);
  
  // Only show in development
  const showBanner = process.env.NODE_ENV === 'development';
  
  if (!showBanner || !isVisible) {
    return null;
  }
  
  return (
    <div className="bg-yellow-50 border-b border-yellow-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between py-3">
          <p className="text-sm text-yellow-800">
            <strong>Development Mode:</strong> Running in development environment.
          </p>
          <button
            onClick={() => setIsVisible(false)}
            className="ml-4 flex-shrink-0 text-yellow-600 hover:text-yellow-500"
          >
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
} 