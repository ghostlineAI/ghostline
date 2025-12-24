# Deployment Checklist - Schema Fix

## 1. Monitor Deployment ⏳
- GitHub Actions: https://github.com/ghostlineAI/api/actions/runs/15998663104
- Wait for "success" status (usually 5-10 minutes)

## 2. Run Database Migrations 🗄️
**CRITICAL: Migrations don't run automatically!**

```bash
# Once deployment is complete, run:
./run_production_migrations.sh
```

## 3. Verify Deployment ✅
```bash
# Check API health
curl https://api.dev.ghostline.ai/health

# Test project creation
curl -X POST https://api.dev.ghostline.ai/api/v1/projects/ \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Project After Fix",
    "subtitle": "Testing schema alignment",
    "genre": "fiction",
    "target_audience": "young_adult",
    "status": "draft",
    "target_page_count": 300,
    "target_word_count": 80000,
    "language": "en"
  }'
```

## 4. If Something Goes Wrong 🚨
```bash
# Quick rollback
./quick_rollback.sh

# Check logs
aws logs tail /ecs/ghostline-api --follow --since 10m
```

## 5. Update Frontend If Needed
The frontend should already be compatible with the new schema (uses 'title' not 'name'). 