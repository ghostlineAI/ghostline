import { readFileSync, existsSync } from 'fs';
import { join } from 'path';
import nextConfig from '../../next.config';

describe('Web Configuration Tests', () => {
  describe('Environment Configuration', () => {
    it('env.production should have valid configuration', () => {
      const envPath = join(__dirname, '../../env.production');
      expect(existsSync(envPath)).toBe(true);
      
      const envContent = readFileSync(envPath, 'utf-8');
      
      // Should have API URL
      expect(envContent).toContain('NEXT_PUBLIC_API_URL=');
      
      // Should use HTTPS for production
      expect(envContent).toContain('https://');
      expect(envContent).not.toContain('http://localhost');
      
      // Should end with /api/v1
      expect(envContent).toMatch(/\/api\/v1\s*$/m);
      
      // Should not have duplicate /api/v1
      expect(envContent).not.toContain('/api/v1/api/v1');
    });
  });

  describe('Next.js Configuration', () => {
    it('should have production-ready settings', () => {
      // Static export for S3 deployment
      expect(nextConfig.output).toBe('export');
      
      // Output directory
      expect(nextConfig.distDir).toBe('out');
      
      // Trailing slash for S3 compatibility
      expect(nextConfig.trailingSlash).toBe(true);
      
      // Should not have hardcoded env variables
      expect(nextConfig.env).toBeUndefined();
    });
    
    it('should have correct image configuration', () => {
      expect(nextConfig.images).toBeDefined();
      expect(nextConfig.images?.unoptimized).toBe(true);
    });
  });

  describe('Package.json Configuration', () => {
    const packagePath = join(__dirname, '../../package.json');
    let packageJson: any;

    beforeAll(() => {
      const content = readFileSync(packagePath, 'utf-8');
      packageJson = JSON.parse(content);
    });

    it('should have all required scripts', () => {
      const requiredScripts = ['dev', 'build', 'start', 'test', 'lint', 'type-check'];
      requiredScripts.forEach(script => {
        expect(packageJson.scripts).toHaveProperty(script);
      });
    });

    it('should have correct Next.js version', () => {
      expect(packageJson.dependencies.next).toBeDefined();
      // Should be using Next.js 15.x
      expect(packageJson.dependencies.next).toMatch(/^\^?15\./);
    });

    it('should have testing dependencies', () => {
      const testingDeps = ['jest', '@testing-library/react', '@testing-library/jest-dom'];
      testingDeps.forEach(dep => {
        expect(packageJson.devDependencies[dep] || packageJson.dependencies[dep]).toBeDefined();
      });
    });
  });

  describe('TypeScript Configuration', () => {
    it('should have tsconfig.json', () => {
      const tsconfigPath = join(__dirname, '../../tsconfig.json');
      expect(existsSync(tsconfigPath)).toBe(true);
      
      const content = readFileSync(tsconfigPath, 'utf-8');
      const tsconfig = JSON.parse(content);
      
      // Should have strict mode
      expect(tsconfig.compilerOptions.strict).toBe(true);
      
      // Should support JSX
      expect(tsconfig.compilerOptions.jsx).toBe('preserve');
    });
  });

  describe('API Client Configuration', () => {
    it('should not hardcode API URL in client files', () => {
      const clientPath = join(__dirname, '../../lib/api/client.ts');
      const clientContent = readFileSync(clientPath, 'utf-8');
      
      // Should use environment variable
      expect(clientContent).toContain('process.env.NEXT_PUBLIC_API_URL');
      
      // Should not hardcode the URL
      expect(clientContent).not.toMatch(/baseURL:\s*['"]https:\/\/api\.dev\.ghostline\.ai/);
      
      // Should have fallback for missing env var
      expect(clientContent).toContain("|| 'http://localhost:8000/api/v1'");
      
      // Should handle HTTP->HTTPS redirect
      expect(clientContent).toContain('location.replace(/^http:/, \'https:\')');
    });
  });
}); 