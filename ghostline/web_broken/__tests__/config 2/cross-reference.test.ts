import nextConfig from '../../next.config';
import { readFileSync } from 'fs';
import { join } from 'path';

describe('Cross-Reference Configuration Tests', () => {
  describe('Build Output Directory Consistency', () => {
    it('next.config distDir should match build expectations', () => {
      // Check that next.config specifies 'out' directory
      expect(nextConfig.distDir).toBe('out');
      
      // Check package.json build script
      const packagePath = join(__dirname, '../../package.json');
      const packageContent = readFileSync(packagePath, 'utf-8');
      const packageJson = JSON.parse(packageContent);
      
      // Should use next build (which respects distDir)
      expect(packageJson.scripts.build).toBe('next build');
    });
  });

  describe('Environment Variables Consistency', () => {
    it('env.production should have correct API URL format', () => {
      // env.production should have the correct format
      const envPath = join(__dirname, '../../env.production');
      const envContent = readFileSync(envPath, 'utf-8');
      expect(envContent.trim()).toBe('NEXT_PUBLIC_API_URL=https://api.dev.ghostline.ai/api/v1');
      
      // Should not have duplicate /api/v1
      expect(envContent).not.toContain('/api/v1/api/v1');
      
      // Should use HTTPS
      expect(envContent).toContain('https://');
    });
  });

  describe('CI Workflow Consistency', () => {
    it('CI workflow should use consistent Node version', () => {
      const ciPath = join(__dirname, '../../.github/workflows/ci.yml');
      const ciContent = readFileSync(ciPath, 'utf-8');
      
      // Extract all Node version references
      const nodeVersionMatches = ciContent.match(/node-version:\s*['"]?(\d+)/g) || [];
      expect(nodeVersionMatches.length).toBeGreaterThan(0);
      
      // All should use the same version
      const versions = nodeVersionMatches.map(match => match.match(/\d+/)![0]);
      const uniqueVersions = [...new Set(versions)];
      expect(uniqueVersions.length).toBe(1);
      expect(uniqueVersions[0]).toBe('20');
    });
    
    it('CI workflow should run tests before build', () => {
      const ciPath = join(__dirname, '../../.github/workflows/ci.yml');
      const ciContent = readFileSync(ciPath, 'utf-8');
      
      // Check job dependencies
      expect(ciContent).toContain('needs: lint');
      expect(ciContent).toContain('needs: test');
      
      // Ensure proper order: lint -> test -> build
      const lintIndex = ciContent.indexOf('jobs:\n  lint:');
      const testIndex = ciContent.indexOf('test:\n    runs-on:');
      const buildIndex = ciContent.indexOf('build:\n    runs-on:');
      
      expect(lintIndex).toBeLessThan(testIndex);
      expect(testIndex).toBeLessThan(buildIndex);
    });
  });

  describe('Node Version Consistency', () => {
    it('Node.js version should be consistent across workflows', () => {
      const ciPath = join(__dirname, '../../.github/workflows/ci.yml');
      const testPath = join(__dirname, '../../.github/workflows/test.yml');
      
      const ciContent = readFileSync(ciPath, 'utf-8');
      const testContent = readFileSync(testPath, 'utf-8');
      
      // Extract Node version from both workflows
      const ciNodeMatch = ciContent.match(/node-version:\s*['"]?(\d+)/);
      const testNodeMatch = testContent.match(/node-version:\s*\[(\d+)/);  // matrix format
      
      expect(ciNodeMatch).toBeTruthy();
      expect(testNodeMatch).toBeTruthy();
      
      // Versions should match
      expect(ciNodeMatch![1]).toBe(testNodeMatch![1]);
    });
  });

  describe('API Endpoint Consistency', () => {
    it('API endpoints should not have /api/v1 prefix in code', () => {
      // Read API client files
      const authPath = join(__dirname, '../../lib/api/auth.ts');
      const authContent = readFileSync(authPath, 'utf-8');
      
      // Check that endpoints don't include /api/v1 and DO include trailing slashes
      expect(authContent).toContain("'/auth/login/'");
      expect(authContent).toContain("'/auth/register/'");
      expect(authContent).toContain("'/users/me/'");
      
      // Should NOT contain /api/v1 in the paths
      expect(authContent).not.toContain("'/api/v1/auth/login'");
      expect(authContent).not.toContain("'/api/v1/auth/register'");
      expect(authContent).not.toContain("'/api/v1/users/me'");
    });
  });
}); 