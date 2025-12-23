import { readFileSync, existsSync } from 'fs';
import { join } from 'path';

describe('CI/CD Critical Structure Tests', () => {
  describe('CI Workflow Critical Steps', () => {
    const workflowPath = join(__dirname, '../../.github/workflows/ci.yml');
    let workflowContent: string;

    beforeAll(() => {
      expect(existsSync(workflowPath)).toBe(true);
      workflowContent = readFileSync(workflowPath, 'utf-8');
    });

    it('should have all critical CI steps in correct order', () => {
      // Critical jobs that must exist
      const criticalJobs = [
        'lint:',
        'test:',
        'build:'
      ];

      let lastIndex = -1;
      criticalJobs.forEach(job => {
        const index = workflowContent.indexOf(job);
        expect(index).toBeGreaterThan(-1);
        expect(index).toBeGreaterThan(lastIndex); // Ensure order
        lastIndex = index;
      });
    });

    it('should have proper job dependencies', () => {
      // Test depends on lint
      expect(workflowContent).toMatch(/test:[\s\S]*?needs: lint/);
      
      // Build depends on test
      expect(workflowContent).toMatch(/build:[\s\S]*?needs: test/);
    });

    it('should only deploy docker on main branch', () => {
      expect(workflowContent).toContain('branches: [ main');
      expect(workflowContent).toContain('if: github.ref == \'refs/heads/main\'');
    });

    it('should use npm ci not npm install', () => {
      expect(workflowContent).toContain('npm ci');
      expect(workflowContent).not.toMatch(/npm install(?!\s|$)/);
    });

    it('should run type checking', () => {
      expect(workflowContent).toContain('npm run type-check');
    });
  });

  describe('Test Workflow Critical Structure', () => {
    const testWorkflowPath = join(__dirname, '../../.github/workflows/test.yml');
    let testWorkflowContent: string;

    beforeAll(() => {
      expect(existsSync(testWorkflowPath)).toBe(true);
      testWorkflowContent = readFileSync(testWorkflowPath, 'utf-8');
    });

    it('should run on both push and pull_request', () => {
      expect(testWorkflowContent).toContain('push:');
      expect(testWorkflowContent).toContain('pull_request:');
    });

    it('should run linter before tests', () => {
      const lintIndex = testWorkflowContent.indexOf('Run linter');
      const testIndex = testWorkflowContent.indexOf('Run tests');
      expect(lintIndex).toBeGreaterThan(-1);
      expect(testIndex).toBeGreaterThan(-1);
      expect(lintIndex).toBeLessThan(testIndex);
    });

    it('should set test environment variables', () => {
      const testStepMatch = testWorkflowContent.match(/- name: Run tests[\s\S]*?(?=- name:|$)/);
      expect(testStepMatch).toBeTruthy();
      
      const testStep = testStepMatch![0];
      expect(testStep).toContain('NEXT_PUBLIC_API_URL: https://api.dev.ghostline.ai/api/v1');
    });
  });

  describe('Package.json Scripts', () => {
    const packagePath = join(__dirname, '../../package.json');
    let packageJson: any;

    beforeAll(() => {
      const content = readFileSync(packagePath, 'utf-8');
      packageJson = JSON.parse(content);
    });

    it('should have all required scripts', () => {
      const requiredScripts = ['dev', 'build', 'start', 'test', 'lint'];
      requiredScripts.forEach(script => {
        expect(packageJson.scripts).toHaveProperty(script);
      });
    });

    it('build script should use next build', () => {
      expect(packageJson.scripts.build).toBe('next build');
    });

    it('test script should use jest', () => {
      expect(packageJson.scripts.test).toBe('jest');
    });
  });
}); 