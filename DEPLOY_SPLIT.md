# Split Deployment Guide

## Frontend (Vercel) + Backend (Render)

This guide shows you how to deploy:
- **Frontend** → Vercel (static hosting, free)
- **Backend** → Render (Python FastAPI, free tier)

**Benefits:**
- ✅ API keys 100% protected on backend
- ✅ Free hosting for both
- ✅ Automatic HTTPS
- ✅ Auto-deploy on git push
- ✅ Separate scaling for frontend/backend

---

## 🎯 Overview

```
┌─────────────────┐
│  Vercel         │
│  (Frontend)     │  ← Users access here
│  Static HTML/   │     https://your-app.vercel.app
│  CSS/JS         │
└────────┬────────┘
         │ API calls
         ▼
┌─────────────────┐
│  Render         │
│  (Backend)      │  ← API server
│  FastAPI Python │     https://your-api.onrender.com
│  + Database     │     (API keys stored here)
└─────────────────┘
```

---

## 📦 Part 1: Deploy Backend to Render

### Step 1.1: Prepare Repository

```bash
# Initialize git (if not done)
cd /Users/lovetyagi/Desktop/RWD_IE_FUNNEL_OPTIMIZER
git init
git branch -m main

# Add all files
git add .
git commit -m "Initial commit for split deployment"

# Push to GitHub
git remote add origin https://github.com/YOUR_USERNAME/rwd-ie-optimizer.git
git push -u origin main
```

### Step 1.2: Create Render Account

1. Go to https://render.com
2. Sign up with GitHub
3. Authorize Render to access your repositories

### Step 1.3: Create New Web Service

1. Click **"New +"** → **"Web Service"**
2. Connect your repository: `rwd-ie-optimizer`
3. Configure:

   **Basic Settings:**
   - Name: `rwd-ie-optimizer-backend`
   - Region: Oregon (US West)
   - Branch: `main`
   - Root Directory: (leave empty)
   - Runtime: `Python 3`

   **Build & Deploy:**
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`

   **Plan:**
   - Select: **Free** (0$/month)
   - Note: Free tier sleeps after 15min inactivity, wakes on request

### Step 1.4: Add Environment Variables (CRITICAL)

Click **"Environment"** tab and add:

```bash
# REQUIRED - AI API Keys (encrypted by Render)
OPENAI_API_KEY=sk-proj-your-actual-key-here
ANTHROPIC_API_KEY=sk-ant-your-actual-key-here

# Frontend URL (will add after Vercel deployment)
FRONTEND_URL=https://your-app.vercel.app

# Optional - Model configuration
MODEL_DEFAULT=gpt-4o
MODEL_RESEARCH=gpt-4-turbo
MODEL_CODING=gpt-4o

# Environment
ENV=production

# Database path
DATABASE_PATH=/opt/render/project/src/data/rwd_claims.db
```

**IMPORTANT:**
- ✅ These are encrypted and secure
- ✅ Never exposed to frontend
- ✅ Only backend can access them

### Step 1.5: Deploy Backend

1. Click **"Create Web Service"**
2. Wait for deployment (~3-5 minutes)
3. You'll get a URL like: `https://rwd-ie-optimizer-backend.onrender.com`

### Step 1.6: Test Backend

```bash
# Replace with your actual Render URL
curl https://rwd-ie-optimizer-backend.onrender.com/health

# Should return:
{
  "status": "healthy",
  "version": "2.0.0",
  "services": {
    "api": "running",
    "database": "connected"
  }
}
```

**Save your backend URL!** You'll need it for frontend configuration.

---

## 🎨 Part 2: Deploy Frontend to Vercel

### Step 2.1: Update Frontend Configuration

Edit `static/config.js`:

```javascript
const config = {
    API_URL: window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : 'https://rwd-ie-optimizer-backend.onrender.com', // ← YOUR RENDER URL
    VERSION: '2.0.0',
    FEATURES: {
        AI_CHAT: true,
        WHAT_IF_ANALYSIS: true,
        SQL_DEBUG: true
    }
};
```

### Step 2.2: Commit Changes

```bash
git add static/config.js
git commit -m "Update API URL for Render backend"
git push
```

### Step 2.3: Create Vercel Account

1. Go to https://vercel.com
2. Sign up with GitHub
3. Authorize Vercel

### Step 2.4: Import Project

1. Click **"Add New..."** → **"Project"**
2. Import your repository: `rwd-ie-optimizer`
3. Configure:

   **Framework Preset:** Other
   **Root Directory:** `./`
   **Build Settings:**
   - Build Command: (leave empty)
   - Output Directory: `static`
   - Install Command: (leave empty)

### Step 2.5: Deploy Frontend

1. Click **"Deploy"**
2. Wait for deployment (~1-2 minutes)
3. You'll get a URL like: `https://rwd-ie-optimizer.vercel.app`

### Step 2.6: Update Backend CORS

Go back to Render:
1. Environment tab
2. Add/Update:
   ```
   FRONTEND_URL=https://rwd-ie-optimizer.vercel.app
   ```
3. Render will auto-redeploy

---

## ✅ Part 3: Verify Deployment

### Test Frontend
1. Open: `https://your-app.vercel.app`
2. Should see RWD IE Optimizer interface

### Test Backend Connection
1. Enter sample criteria in frontend
2. Click "Process Criteria"
3. Should complete successfully

### Test API Directly
```bash
curl https://your-backend.onrender.com/api/database-info
```

### Verify Security
1. Open browser DevTools → Network tab
2. Make a request
3. Check: No API keys in headers/responses
4. Confirm: All API calls go to Render backend

---

## 🔒 Security Verification Checklist

- [ ] API keys only in Render environment variables
- [ ] No API keys in code or git
- [ ] Frontend calls backend API only
- [ ] CORS configured (frontend URL in backend)
- [ ] HTTPS enabled on both deployments
- [ ] No secrets visible in browser DevTools

---

## 🔄 Continuous Deployment

### Auto-Deploy Setup

**Backend (Render):**
- ✅ Auto-deploys on push to `main` branch
- ✅ Configure in Render → Settings → Auto-Deploy

**Frontend (Vercel):**
- ✅ Auto-deploys on push to any branch
- ✅ Main branch → Production
- ✅ Other branches → Preview URLs

### Workflow

```bash
# Make changes
git add .
git commit -m "Add new feature"
git push

# Automatic:
# 1. Render detects push → Deploys backend
# 2. Vercel detects push → Deploys frontend
# 3. Both live in ~5 minutes
```

---

## 💰 Cost Breakdown

### Free Tier Limits

**Vercel (Frontend):**
- ✅ 100 GB bandwidth/month
- ✅ Unlimited sites
- ✅ Automatic HTTPS
- ✅ CDN included
- **Cost:** $0/month

**Render (Backend):**
- ✅ 750 hours/month compute
- ✅ Sleeps after 15min inactivity
- ✅ Automatic HTTPS
- ✅ 500MB storage
- **Cost:** $0/month
- **Note:** Cold starts (~30sec) on free tier

**Total:** $0/month for both!

### When to Upgrade

**Vercel Pro ($20/month):**
- Custom domains
- Team collaboration
- Analytics

**Render Starter ($7/month):**
- No cold starts
- Always-on service
- 1GB RAM

---

## 🐛 Troubleshooting

### Frontend can't connect to backend

**Error:** Network error or CORS error

**Solutions:**
1. Check `static/config.js` has correct Render URL
2. Verify CORS in Render environment variables:
   ```
   FRONTEND_URL=https://your-app.vercel.app
   ```
3. Check Render logs for errors

### Backend cold start delays

**Issue:** First request takes 30+ seconds

**Explanation:** Free tier sleeps after 15min inactivity

**Solutions:**
- Accept it (free tier limitation)
- Upgrade to Render Starter ($7/month)
- Use cron job to ping every 10 minutes

### API keys not working

**Error:** `No API key configured`

**Solutions:**
1. Verify keys in Render environment variables
2. Check variable names match exactly
3. Redeploy backend
4. Check Render logs for errors

### Database errors

**Error:** `Database not found`

**Solutions:**
1. Ensure `data/rwd_claims.db` is in repository
2. Check `DATABASE_PATH` environment variable
3. Consider using external database (Neon, Supabase)

---

## 📊 URLs Reference

After deployment, save these URLs:

```
Frontend (Vercel):  https://_____________________.vercel.app
Backend (Render):   https://_____________________.onrender.com
API Documentation:  https://_____________________.onrender.com/api/docs
```

---

## 🚀 Quick Commands Reference

### Deploy Backend (Render)
```bash
git add .
git commit -m "Update backend"
git push  # Auto-deploys to Render
```

### Deploy Frontend (Vercel)
```bash
git add static/
git commit -m "Update frontend"
git push  # Auto-deploys to Vercel
```

### View Logs

**Render:**
- Dashboard → Your Service → Logs tab
- Or: `curl https://your-backend.onrender.com/health`

**Vercel:**
- Dashboard → Deployments → Click deployment → Functions tab

---

## 🎉 Success!

You now have:
- ✅ Frontend on Vercel (fast CDN)
- ✅ Backend on Render (Python FastAPI)
- ✅ API keys secured (backend only)
- ✅ Auto-deploy on git push
- ✅ Free hosting for both!

**Next Steps:**
1. Custom domain (optional)
2. Analytics setup
3. Monitoring/alerts
4. Database upgrade (if needed)

---

## 📞 Support

**Render:**
- Docs: https://render.com/docs
- Community: https://community.render.com

**Vercel:**
- Docs: https://vercel.com/docs
- Support: https://vercel.com/support

**Application Issues:**
- Check deployment logs
- Test locally first
- Review environment variables

---

**Deployment Date:** ______________
**Frontend URL:** ______________
**Backend URL:** ______________
**Deployed By:** ______________
