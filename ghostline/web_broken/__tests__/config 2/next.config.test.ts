import nextConfig from '../../next.config';

describe('Next.js Configuration', () => {
  it('should have output set to export for static generation', () => {
    expect(nextConfig.output).toBe('export');
  });

  it('should have distDir set to out', () => {
    expect(nextConfig.distDir).toBe('out');
  });

  it('should have trailingSlash enabled', () => {
    expect(nextConfig.trailingSlash).toBe(true);
  });

  it('should have images unoptimized for static export', () => {
    expect(nextConfig.images?.unoptimized).toBe(true);
  });

  it('should not have environment variables hardcoded', () => {
    // Environment variables should not be set in next.config
    // They should come from build-time environment
    expect(nextConfig.env).toBeUndefined();
  });

  it('should not ignore ESLint errors during build', () => {
    expect(nextConfig.eslint?.ignoreDuringBuilds).toBe(false);
  });

  it('should not ignore TypeScript errors during build', () => {
    expect(nextConfig.typescript?.ignoreBuildErrors).toBe(false);
  });
}); 