'use client';

import { useState } from 'react';
import { useAuthStore } from '@/lib/stores/auth';
import apiClient from '@/lib/api/client';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export default function TestPage() {
  const { user, token } = useAuthStore();
  const [result, setResult] = useState<string>('');
  const [loading, setLoading] = useState(false);

  const testProjects = async () => {
    setLoading(true);
    setResult('Testing projects endpoint...\n');
    
    try {
      const response = await apiClient.get('/projects');
      setResult(prev => prev + `Success! Status: ${response.status}\n`);
      setResult(prev => prev + `Data: ${JSON.stringify(response.data, null, 2)}\n`);
    } catch (error: unknown) {
      const err = error as { response?: { status: number; data: unknown } };
      setResult(prev => prev + `Error! Status: ${err.response?.status}\n`);
      setResult(prev => prev + `Error data: ${JSON.stringify(err.response?.data, null, 2)}\n`);
    }
    
    setLoading(false);
  };

  const testUserInfo = async () => {
    setLoading(true);
    setResult('Testing user info endpoint...\n');
    
    try {
      const response = await apiClient.get('/users/me');
      setResult(prev => prev + `Success! Status: ${response.status}\n`);
      setResult(prev => prev + `Data: ${JSON.stringify(response.data, null, 2)}\n`);
    } catch (error: unknown) {
      const err = error as { response?: { status: number; data: unknown } };
      setResult(prev => prev + `Error! Status: ${err.response?.status}\n`);
      setResult(prev => prev + `Error data: ${JSON.stringify(err.response?.data, null, 2)}\n`);
    }
    
    setLoading(false);
  };

  return (
    <div className="p-6 space-y-6">
      <h1 className="text-2xl font-bold">API Test Page</h1>
      
      <Card>
        <CardHeader>
          <CardTitle>Current Auth State</CardTitle>
        </CardHeader>
        <CardContent>
          <p><strong>User:</strong> {user ? user.email : 'Not logged in'}</p>
          <p><strong>Token:</strong> {token ? `${token.substring(0, 20)}...` : 'No token'}</p>
        </CardContent>
      </Card>
      
      <Card>
        <CardHeader>
          <CardTitle>API Tests</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex gap-4">
            <Button onClick={testProjects} disabled={loading}>
              Test Projects Endpoint
            </Button>
            <Button onClick={testUserInfo} disabled={loading}>
              Test User Info Endpoint
            </Button>
          </div>
          
          {result && (
            <pre className="bg-gray-100 p-4 rounded overflow-auto max-h-96">
              {result}
            </pre>
          )}
        </CardContent>
      </Card>
    </div>
  );
} 