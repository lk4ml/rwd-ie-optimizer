# Vercel Deployment Guide

## 🚀 Deploy RWD IE Optimizer to Vercel

This guide walks you through deploying your application to Vercel with secure API key management.

---

## 📋 Prerequisites

- Vercel account (free tier works)
- Git repository (GitHub, GitLab, or Bitbucket)
- OpenAI API key
- Anthropic API key (optional)

---

## 🔐 Security First: API Key Protection

**IMPORTANT:** Your API keys will be stored as **encrypted environment variables** in Vercel. They will NEVER be exposed in your code or browser.

### How It Works

1. ✅ API keys stored in Vercel's encrypted environment
2. ✅ Keys only accessible by serverless functions (backend)
3. ✅ Never sent to browser/frontend
4. ✅ Automatic encryption at rest
5. ✅ Can be rotated without redeploying code

---

## 🎯 Step-by-Step Deployment

### Step 1: Prepare Your Repository

```bash
# Initialize git (if not already done)
git init

# Add all files
git add .

# Commit
git commit -m "Initial commit for Vercel deployment"

# Create GitHub repository and push
git remote add origin https://github.com/YOUR_USERNAME/rwd-ie-optimizer.git
git branch -M main
git push -u origin main
```

### Step 2: Connect to Vercel

1. Go to https://vercel.com
2. Click **"New Project"**
3. Import your Git repository
4. Select the repository: `rwd-ie-optimizer`

### Step 3: Configure Project Settings

**Framework Preset:** Other
**Build Command:** (leave empty)
**Output Directory:** (leave empty)
**Install Command:** `pip install -r requirements.txt`

### Step 4: Add Environment Variables (CRITICAL)

Click **"Environment Variables"** and add:

#### Required Variables

```bash
# OpenAI API Key (REQUIRED)
OPENAI_API_KEY=sk-proj-your-actual-key-here

# Anthropic API Key (OPTIONAL - for AI chat)
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here
```

#### Optional Configuration

```bash
# Model Settings
MODEL_DEFAULT=gpt-4o
MODEL_RESEARCH=gpt-4-turbo
MODEL_CODING=gpt-4o

# Limits
MAX_TOKENS=2000
QUERY_TIMEOUT_SECONDS=30

# Database (Note: SQLite doesn't work well on Vercel)
DATABASE_PATH=/tmp/rwd_claims.db
```

**Important Notes:**
- ✅ Click "Production", "Preview", and "Development" for each variable
- ✅ These are encrypted and never exposed to the client
- ✅ Can be updated anytime in Vercel dashboard

### Step 5: Deploy

Click **"Deploy"**

Vercel will:
1. Clone your repository
2. Install Python dependencies
3. Build the serverless functions
4. Deploy to CDN

⏱️ First deployment takes 2-3 minutes.

### Step 6: Verify Deployment

Once deployed, you'll get a URL like:
```
https://rwd-ie-optimizer.vercel.app
```

Test the deployment:
```bash
# Check health endpoint
curl https://your-app.vercel.app/api/health

# Should return:
{
  "status": "healthy",
  "version": "2.0.0",
  "environment": "vercel"
}
```

---

## 🔒 API Key Security Features

### What's Protected

✅ **Environment Variables:**
- Encrypted at rest in Vercel's infrastructure
- Only accessible to serverless functions
- Never exposed to browser

✅ **Backend-Only Access:**
```python
# This runs on Vercel's servers (secure)
from src.services import get_ai_service

ai = get_ai_service()  # Uses env var internally
result = ai.parse_criteria(text)  # Key never leaves server
```

✅ **Frontend Has No Access:**
```javascript
// Browser JavaScript CANNOT access API keys
// All AI calls go through your backend API
fetch('/api/process-criteria', {
  method: 'POST',
  body: JSON.stringify({criteria_text: '...'})
})
```

### How to Verify Security

1. **Check Network Tab** (Browser DevTools)
   - No API keys in request/response headers
   - No keys in URLs
   - No keys in request bodies

2. **View Page Source**
   - No API keys in HTML
   - No keys in JavaScript

3. **Check Vercel Dashboard**
   - Environment variables shown as `••••••••`
   - "Hidden" status for sensitive values

---

## 📊 Database Considerations

### ⚠️ SQLite Limitation on Vercel

Vercel's serverless functions have read-only file systems. SQLite doesn't work well for this use case.

### Solutions

#### Option 1: Use Vercel Postgres (Recommended)

```bash
# Install Vercel Postgres integration
vercel postgres create

# Update environment variable
DATABASE_URL=postgres://...
```

Update `src/tools/sql_executor.py` to use PostgreSQL instead of SQLite.

#### Option 2: Use Neon, PlanetScale, or Supabase

Free tier options:
- **Neon** - Serverless Postgres (https://neon.tech)
- **PlanetScale** - MySQL (https://planetscale.com)
- **Supabase** - Postgres (https://supabase.com)

#### Option 3: Upload Sample Data on Each Request (Demo Only)

For demos, you can use in-memory SQLite with sample data:

```python
# Create temp database on each function invocation
import sqlite3
conn = sqlite3.connect(':memory:')
# Load sample data
```

**Note:** This adds latency to each request.

---

## 🔄 Continuous Deployment

### Auto-Deploy on Git Push

Vercel automatically deploys when you push to GitHub:

```bash
# Make changes
git add .
git commit -m "Update feature X"
git push

# Vercel automatically:
# 1. Detects push
# 2. Builds new version
# 3. Deploys to preview URL
# 4. Deploys to production (if on main branch)
```

### Preview Deployments

Every pull request gets a unique preview URL:
```
https://rwd-ie-optimizer-git-feature-x.vercel.app
```

---

## 🛠️ Managing Environment Variables

### View/Edit Variables

1. Go to Vercel Dashboard
2. Select your project
3. Settings → Environment Variables
4. Click ⋯ menu → Edit or Delete

### Rotate API Keys

```bash
# Update in Vercel Dashboard
1. Settings → Environment Variables
2. Edit OPENAI_API_KEY
3. Enter new key
4. Click "Save"

# Redeploy (optional)
vercel --prod
```

**Note:** Changes take effect on next deployment or serverless function cold start.

### Different Keys for Environments

You can set different keys for:
- **Production** - Live users
- **Preview** - Pull request previews
- **Development** - Local testing

---

## 📈 Monitoring & Logs

### View Logs

1. Vercel Dashboard → Your Project
2. Deployments → Click on deployment
3. Functions → View logs

### Real-Time Logs

```bash
# Install Vercel CLI
npm i -g vercel

# Login
vercel login

# View logs
vercel logs
```

### Error Tracking

Consider integrating:
- **Sentry** - Error tracking
- **LogRocket** - Session replay
- **Datadog** - Full observability

---

## 🚨 Troubleshooting

### Deployment Fails

**Error:** `pip install failed`

**Solution:**
```bash
# Check requirements.txt syntax
pip install -r requirements.txt  # Test locally

# Ensure Python 3.12 compatible packages
```

**Error:** `Module not found`

**Solution:**
```bash
# Check import paths in api/index.py
# Ensure src/ directory structure is correct
```

### API Keys Not Working

**Error:** `No API key configured`

**Solution:**
1. Verify environment variable names match exactly
2. Check variable is enabled for "Production"
3. Redeploy: `vercel --prod`

### Database Errors

**Error:** `Database not found`

**Solution:**
- SQLite doesn't work on Vercel
- Use Vercel Postgres or external database
- See "Database Considerations" above

### Slow Response Times

**Cause:** Cold starts on serverless functions

**Solutions:**
- Upgrade to Vercel Pro (keeps functions warm)
- Optimize imports (lazy loading)
- Use edge functions for static responses

---

## 💰 Cost Considerations

### Free Tier Limits (Hobby Plan)

- ✅ 100 GB bandwidth/month
- ✅ 100 hours serverless function execution
- ✅ Unlimited deployments
- ✅ Unlimited team members (personal projects)

### When to Upgrade (Pro Plan - $20/month)

- Need custom domains
- Want zero cold starts
- Require team collaboration
- Need advanced analytics

### API Costs

**OpenAI:**
- GPT-4o: $2.50 per 1M input tokens
- GPT-4-turbo: $10 per 1M input tokens

**Anthropic:**
- Claude Sonnet 4: $3 per 1M input tokens

**Estimated monthly cost for 1000 queries:** ~$5-10

---

## 🔐 Security Best Practices

### ✅ Do's

- ✅ Use environment variables for ALL secrets
- ✅ Enable Vercel's automatic HTTPS
- ✅ Use CORS properly (restrict origins in production)
- ✅ Validate all user inputs
- ✅ Rate limit API endpoints
- ✅ Monitor usage and logs

### ❌ Don'ts

- ❌ Never commit .env to git
- ❌ Never expose API keys in frontend
- ❌ Never trust user input without validation
- ❌ Don't disable CORS in production
- ❌ Don't hardcode secrets in code

---

## 🎯 Post-Deployment Checklist

- [ ] Application loads at Vercel URL
- [ ] Health endpoint returns "healthy"
- [ ] Can process sample criteria
- [ ] SQL execution works
- [ ] AI chat responds (if Anthropic key set)
- [ ] What-If analysis works
- [ ] No API keys visible in browser
- [ ] Environment variables set correctly
- [ ] Custom domain configured (optional)
- [ ] Analytics/monitoring enabled (optional)

---

## 📞 Support

**Vercel Issues:**
- Documentation: https://vercel.com/docs
- Support: https://vercel.com/support
- Community: https://github.com/vercel/vercel/discussions

**Application Issues:**
- Check Vercel logs
- Review environment variables
- Test locally first: `python main.py`

---

## 🚀 Quick Deploy Button (Optional)

Add this to your README.md:

```markdown
[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https://github.com/YOUR_USERNAME/rwd-ie-optimizer&env=OPENAI_API_KEY,ANTHROPIC_API_KEY&envDescription=API%20keys%20required%20for%20AI%20features&envLink=https://platform.openai.com/api-keys)
```

This creates a one-click deploy button!

---

**Happy Deploying! 🎉**

Your API keys are secure, your app is live, and your users can start analyzing clinical trial criteria!
