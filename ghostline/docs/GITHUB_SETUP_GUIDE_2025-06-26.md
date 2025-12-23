---
Last Updated: 2025-06-28 09:30:52 PDT
---

# GitHub Setup Guide for GhostLine AI

## Quick Setup Steps

### 1. Create Repositories on GitHub

Go to https://github.com/ghostlineAI and create these 5 repositories:

1. **web** - GhostLine web frontend application
2. **api** - GhostLine backend API service  
3. **agents** - GhostLine AI agent system
4. **infra** - GhostLine infrastructure as code
5. **docs** - GhostLine documentation

For each repository:
- Set visibility to **Private**
- DO NOT initialize with README, .gitignore, or license
- Leave all initialization options unchecked

### 2. Set Up Authentication

You'll need one of these:
- **Personal Access Token** (recommended for HTTPS)
  - Go to Settings → Developer settings → Personal access tokens → Tokens (classic)
  - Generate new token with `repo` scope
  - Save the token securely

### 3. Push the Code

Run the push script:
```bash
./push_to_github.sh
```

When prompted for credentials:
- Username: `asgeorges`
- Password: Use your Personal Access Token (not your GitHub password)

### 4. Configure Branch Protection (After Push)

For each repository:
1. Go to Settings → Branches
2. Add rule for `main` branch
3. Enable:
   - Require pull request reviews before merging
   - Require status checks to pass before merging
   - Add `markdown-lint` as required status check
   - Include administrators

### 5. Organization Settings

1. Invite team members at https://github.com/orgs/ghostlineAI/people
2. Configure team permissions
3. Enable 2FA requirement for the organization

## Troubleshooting

If you get authentication errors:
- Make sure you're using the Personal Access Token, not your password
- Ensure the token has `repo` scope
- Check that the repositories were created as private

## Next Steps

Once all repositories are pushed:
1. Verify GitHub Actions are running (check Actions tab)
2. Create development branches
3. Begin Phase 1: Open-Source Capability Scan 