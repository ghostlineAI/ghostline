# Project Detail Page Solution for Static Export

## Problem
Next.js static export (`output: 'export'`) does not support dynamic routes like `/projects/[id]` without `generateStaticParams()`. Since project IDs are created at runtime, we cannot pre-generate all possible pages.

## Current Fix (Temporary)
- Removed dynamic route that was causing 404 errors
- Redirect to projects list after creation
- Disabled "Open" and "Edit" buttons

## Proper Solutions

### Option 1: Client-Side State Management (Recommended)
Use Zustand or React Context to store selected project, then navigate to a static page that reads from state.

```typescript
// In projects list:
const handleOpenProject = (project) => {
  projectStore.setSelectedProject(project);
  router.push('/dashboard/project-detail');
};

// In static project-detail page:
const project = projectStore.selectedProject;
if (!project) {
  router.push('/dashboard/projects');
}
```

### Option 2: Query Parameters
Use URL query parameters instead of dynamic routes:
```
/dashboard/projects?view=detail&id=xxx
```

### Option 3: Remove Static Export
Switch to SSR or SSG with ISR, but this requires infrastructure changes.

## Implementation Plan
1. Create project store using existing Zustand setup
2. Add static project-detail page
3. Update navigation to use store
4. Add loading state for direct URL access
5. Test thoroughly with e2e tests 