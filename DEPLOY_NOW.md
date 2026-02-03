# 🚀 Deploy NOW - Quick Start Guide

Follow these steps to deploy your application in the next 15 minutes!

---

## ✅ What You Need

- [ ] GitHub account
- [ ] Render account (free) - https://render.com
- [ ] Vercel account (free) - https://vercel.com
- [ ] Your OpenAI API key
- [ ] Your Anthropic API key (optional)

---

## 📝 Step 1: Push to GitHub (2 minutes)

### Create GitHub Repository

1. Go to https://github.com/new
2. Repository name: `rwd-ie-optimizer`
3. Set to **Public** or **Private**
4. **DO NOT** initialize with README
5. Click **"Create repository"**

### Push Your Code

```bash
# You're already in the correct directory
# Git is already initialized
# Files are already committed

# Add your GitHub repository as remote (REPLACE WITH YOUR URL)
git remote add origin https://github.com/YOUR_USERNAME/rwd-ie-optimizer.git

# Push to GitHub
git push -u origin main
```

✅ **Checkpoint:** Refresh GitHub - you should see all your files!

---

## 🔧 Step 2: Deploy Backend to Render (5 minutes)

### 2.1 Sign Up

1. Go to https://render.com
2. Click **"Get Started"**
3. Sign up with GitHub
4. Authorize Render

### 2.2 Create Web Service

1. Click **"New +"** → **"Web Service"**
2. Click **"Connect account"** (if needed)
3. Find and select `rwd-ie-optimizer`
4. Click **"Connect"**

### 2.3 Configure Service

Fill in these fields:

**Name:** `rwd-ie-optimizer-backend` (or any name you like)

**Region:** Oregon (or closest to you)

**Branch:** `main`

**Root Directory:** (leave empty)

**Runtime:** `Python 3`

**Build Command:**
```
pip install -r requirements.txt
```

**Start Command:**
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```

**Instance Type:** `Free`

### 2.4 Add Environment Variables

Scroll down to **"Environment Variables"**

Click **"Add Environment Variable"** and add these:

```
OPENAI_API_KEY=sk-proj-YOUR-ACTUAL-KEY-HERE
```

Click **"Add Environment Variable"** again:

```
ANTHROPIC_API_KEY=sk-ant-YOUR-ACTUAL-KEY-HERE
```

Optional (recommended):

```
MODEL_DEFAULT=gpt-4o
MODEL_RESEARCH=gpt-4-turbo
MODEL_CODING=gpt-4o
ENV=production
```

### 2.5 Deploy!

1. Scroll to bottom
2. Click **"Create Web Service"**
3. Wait 3-5 minutes for deployment

**✅ Checkpoint:** You'll see "Your service is live!" and get a URL like:
```
https://rwd-ie-optimizer-backend-xxxx.onrender.com
```

**SAVE THIS URL!** You need it for the next step.

### 2.6 Test Backend

```bash
# Replace with YOUR actual Render URL
curl https://rwd-ie-optimizer-backend-xxxx.onrender.com/health

# Should return:
{"status":"healthy","version":"2.0.0","services":{"api":"running","database":"connected"}}
```

✅ **Backend is LIVE!**

---

## 🎨 Step 3: Update Frontend Config (1 minute)

### Edit config.js

1. Open `static/config.js` in your code editor
2. Replace the API_URL with YOUR Render URL:

```javascript
const config = {
    API_URL: window.location.hostname === 'localhost'
        ? 'http://localhost:8000'
        : 'https://rwd-ie-optimizer-backend-xxxx.onrender.com', // ← YOUR RENDER URL HERE
    VERSION: '2.0.0',
    FEATURES: {
        AI_CHAT: true,
        WHAT_IF_ANALYSIS: true,
        SQL_DEBUG: true
    }
};
```

3. Save the file

### Push Changes

```bash
git add static/config.js
git commit -m "Update API URL for Render backend"
git push
```

---

## 🌐 Step 4: Deploy Frontend to Vercel (3 minutes)

### 4.1 Sign Up

1. Go to https://vercel.com
2. Click **"Sign Up"**
3. Sign up with GitHub
4. Authorize Vercel

### 4.2 Import Project

1. Click **"Add New..."** → **"Project"**
2. Find `rwd-ie-optimizer` repository
3. Click **"Import"**

### 4.3 Configure Project

**Framework Preset:** Other

**Root Directory:** `./`

**Build Command:** (leave empty)

**Output Directory:** `static`

**Install Command:** (leave empty)

### 4.4 Deploy!

1. Click **"Deploy"**
2. Wait 1-2 minutes

**✅ Checkpoint:** You'll see "Congratulations!" and get a URL like:
```
https://rwd-ie-optimizer-xxxx.vercel.app
```

**SAVE THIS URL!**

---

## 🔄 Step 5: Update Backend CORS (2 minutes)

### Add Frontend URL to Backend

1. Go back to Render dashboard
2. Select `rwd-ie-optimizer-backend`
3. Click **"Environment"** tab
4. Click **"Add Environment Variable"**
5. Add:

```
FRONTEND_URL=https://rwd-ie-optimizer-xxxx.vercel.app
```

(Use YOUR actual Vercel URL)

6. Click **"Save Changes"**

**Render will automatically redeploy (~1 minute)**

---

## ✨ Step 6: TEST YOUR DEPLOYMENT! (2 minutes)

### 6.1 Open Your App

Go to your Vercel URL:
```
https://rwd-ie-optimizer-xxxx.vercel.app
```

### 6.2 Test the Workflow

1. **Enter sample criteria:**
```
INCLUSION CRITERIA:
1. Adults aged 18 to 75 years
2. Type 2 Diabetes Mellitus diagnosis
3. Currently on Metformin therapy

EXCLUSION CRITERIA:
1. History of heart failure
2. Active cancer diagnosis
```

2. Click **"Process Criteria"**

3. Watch the stages complete:
   - ✅ Stage 1: IE Interpreter
   - ✅ Stage 2: Deep Research
   - ✅ Stage 3: Coding Agent
   - ✅ Stage 4: SQL Runner
   - ✅ Stage 5: Funnel Analysis

4. Verify you see:
   - Generated SQL
   - Patient counts
   - Funnel visualization

### 6.3 Test AI Chat (Optional)

1. Click **"AI Assistance"** in SQL editor
2. Type: "Explain this query"
3. Should get Claude's response

### 6.4 Verify Security

1. Open Browser DevTools (F12)
2. Go to **Network** tab
3. Process criteria again
4. Check requests - **NO API KEYS should be visible!**

✅ **Security verified - API keys are protected!**

---

## 🎉 SUCCESS!

**You now have:**

✅ **Frontend:** https://_________________.vercel.app
✅ **Backend:** https://_________________.onrender.com
✅ **API Keys:** Secured on backend (encrypted)
✅ **Auto-Deploy:** Enabled on git push
✅ **Free Hosting:** Both platforms!

---

## 📋 Save Your URLs

**Frontend (Vercel):**
```
https://_________________.vercel.app
```

**Backend (Render):**
```
https://_________________.onrender.com
```

**API Documentation:**
```
https://_________________.onrender.com/api/docs
```

---

## 🔒 Security Checklist

- [x] API keys stored in Render (encrypted)
- [x] No API keys in code or git
- [x] Frontend calls backend API only
- [x] CORS configured
- [x] HTTPS enabled
- [x] No secrets in browser

---

## ⚠️ Important Notes

### Free Tier Limitations

**Render Free Tier:**
- ⚠️ Sleeps after 15 minutes of inactivity
- ⚠️ Cold start: ~30 seconds on first request
- ✅ Perfect for demos and development
- 💰 Upgrade to Starter ($7/month) for always-on

**Vercel Free Tier:**
- ✅ No sleep/cold starts
- ✅ Fast CDN delivery
- ✅ Perfect for production

### Database Note

The SQLite database works on Render but has limitations. For production, consider:
- Neon (free PostgreSQL)
- Supabase (free PostgreSQL)
- Vercel Postgres

See `DEPLOY_SPLIT.md` for database migration guide.

---

## 🔄 Making Changes

### Update Frontend

```bash
# Edit files in static/
git add static/
git commit -m "Update frontend"
git push  # Auto-deploys to Vercel
```

### Update Backend

```bash
# Edit Python files
git add .
git commit -m "Update backend"
git push  # Auto-deploys to Render
```

Both deploy automatically!

---

## 🐛 Troubleshooting

### Frontend shows "Network Error"

**Fix:**
1. Check `static/config.js` has correct Render URL
2. Wait for Render to wake up (~30 sec)
3. Check Render logs for errors

### "No API key configured"

**Fix:**
1. Go to Render → Environment
2. Verify `OPENAI_API_KEY` is set
3. Click **"Manual Deploy"** to redeploy

### Backend not responding

**Fix:**
- Free tier sleeps after 15min
- First request wakes it up (~30 sec)
- Subsequent requests are fast

---

## 📞 Need Help?

1. Check `DEPLOY_SPLIT.md` for detailed troubleshooting
2. Check Render logs: Dashboard → Logs tab
3. Check Vercel logs: Dashboard → Functions → Logs

---

## 🎯 Next Steps (Optional)

- [ ] Add custom domain
- [ ] Set up monitoring
- [ ] Upgrade to paid tiers (no cold starts)
- [ ] Migrate to external database
- [ ] Add team members

---

**Deployment Date:** _______________

**Time to Deploy:** ~15 minutes

**Status:** 🎉 DEPLOYED!
