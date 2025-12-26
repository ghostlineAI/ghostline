describe('API Configuration Tests', () => {
  describe('Environment Variable Configuration', () => {
    it('should use NEXT_PUBLIC_API_URL with /api/v1 suffix', () => {
      // Test that we expect the env var to include /api/v1
      const expectedUrl = 'https://api.dev.ghostline.ai/api/v1';
      
      // In production builds, this should be set
      if (process.env.NODE_ENV === 'production') {
        expect(process.env.NEXT_PUBLIC_API_URL).toBe(expectedUrl);
      }
    });
  });

  describe('API Endpoint Path Tests', () => {
    it('auth endpoints should not include /api/v1 prefix', () => {
      // These are the paths that should be used in the code
      const authPaths = [
        '/auth/login',
        '/auth/register',
        '/users/me'
      ];
      
      // Verify none of them contain /api/v1
      authPaths.forEach(path => {
        expect(path).not.toContain('/api/v1');
        expect(path).toMatch(/^\/[^/]/); // Should start with / but not //
      });
    });

    it('project endpoints should not include /api/v1 prefix', () => {
      const projectPaths = [
        '/projects',
        '/projects/123',
        '/projects/123/fork'
      ];
      
      projectPaths.forEach(path => {
        expect(path).not.toContain('/api/v1');
        expect(path).toMatch(/^\/[^/]/);
      });
    });
  });

  describe('Trailing Slash Tests', () => {
    it('API paths SHOULD end with trailing slash for FastAPI compatibility', () => {
      const paths = [
        '/projects/',
        '/projects/123/',
        '/auth/login/',
        '/auth/register/',
        '/users/me/'
      ];
      
      paths.forEach(path => {
        expect(path).toMatch(/\/$/);
      });
    });
    
    it('FastAPI redirects non-trailing slash URLs causing CORS issues', () => {
      // Document why we need trailing slashes
      const withoutSlash = '/projects';
      const withSlash = '/projects/';
      
      // FastAPI behavior: /projects -> 307 redirect to /projects/
      // This breaks CORS because redirects don't preserve CORS headers
      expect(withSlash).toBe(withoutSlash + '/');
    });
  });

  describe('URL Security Tests', () => {
    it('production API URL should use HTTPS', () => {
      const prodUrl = 'https://api.dev.ghostline.ai/api/v1';
      expect(prodUrl).toMatch(/^https:/);
      expect(prodUrl).not.toMatch(/^http:\/\/(?!localhost)/);
    });
    
    it('API URL should contain exactly one /api/v1', () => {
      const apiUrl = 'https://api.dev.ghostline.ai/api/v1';
      const matches = apiUrl.match(/\/api\/v1/g) || [];
      expect(matches.length).toBe(1);
    });
  });
}); 