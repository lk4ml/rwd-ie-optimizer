# Vercel Deployment Checklist

Use this checklist to ensure a smooth deployment with secure API key management.

## 🔐 Pre-Deployment Security

- [ ] **.env file is in .gitignore** (verified)
- [ ] **No API keys in code** (verified)
- [ ] **API keys only in environment variables** (verified)
- [ ] **All secrets removed from static files** (verified)

## 📦 Repository Preparation

- [ ] **Git repository initialized**
  ```bash
  git init
  ```

- [ ] **All files committed**
  ```bash
  git add .
  git commit -m "Initial commit for Vercel"
  ```

- [ ] **Pushed to GitHub/GitLab**
  ```bash
  git remote add origin https://github.com/YOUR_USERNAME/rwd-ie-optimizer.git
  git push -u origin main
  ```

## 🚀 Vercel Setup

- [ ] **Signed up for Vercel account**
  - Go to https://vercel.com
  - Sign up with GitHub/GitLab

- [ ] **Created new project**
  - Click "New Project"
  - Import Git repository
  - Select `rwd-ie-optimizer`

- [ ] **Configured build settings**
  - Framework: Other
  - Build Command: (empty)
  - Output Directory: (empty)
  - Install Command: `pip install -r requirements.txt`

## 🔑 Environment Variables (CRITICAL)

- [ ] **Added OPENAI_API_KEY**
  - Name: `OPENAI_API_KEY`
  - Value: `sk-proj-your-actual-key`
  - Environments: ✅ Production ✅ Preview ✅ Development

- [ ] **Added ANTHROPIC_API_KEY** (if using AI chat)
  - Name: `ANTHROPIC_API_KEY`
  - Value: `sk-ant-your-actual-key`
  - Environments: ✅ Production ✅ Preview ✅ Development

- [ ] **Added optional configuration** (if needed)
  - `MODEL_DEFAULT`
  - `MODEL_RESEARCH`
  - `MODEL_CODING`
  - `MAX_TOKENS`
  - `QUERY_TIMEOUT_SECONDS`

## 🎯 Deployment

- [ ] **Clicked "Deploy" button**

- [ ] **Waited for build to complete** (~2-3 minutes)

- [ ] **Noted deployment URL**
  - Production: `https://your-project.vercel.app`
  - Save this URL!

## ✅ Post-Deployment Verification

- [ ] **Health check works**
  ```bash
  curl https://your-project.vercel.app/api/health
  # Should return: {"status":"healthy","version":"2.0.0"}
  ```

- [ ] **Frontend loads**
  - Open: https://your-project.vercel.app
  - Should see RWD IE Optimizer interface

- [ ] **Can process criteria**
  - Enter sample criteria
  - Click "Process Criteria"
  - Should complete successfully

- [ ] **SQL execution works**
  - Generated SQL appears in editor
  - Can run queries
  - Results display correctly

- [ ] **AI chat works** (if Anthropic key set)
  - Click "AI Assistance"
  - Send message
  - Get response from Claude

- [ ] **What-If analysis works**
  - Go to "What If Analysis" tab
  - Toggle criteria
  - Funnel updates in real-time

## 🔒 Security Verification

- [ ] **No API keys in browser**
  - Open DevTools → Network tab
  - Check requests/responses
  - Confirm: No API keys visible

- [ ] **Environment variables hidden**
  - Vercel Dashboard → Environment Variables
  - Should show: `••••••••` (masked)

- [ ] **Page source has no secrets**
  - View page source
  - Search for: "sk-proj", "sk-ant"
  - Confirm: Not found

- [ ] **HTTPS enabled**
  - URL starts with https://
  - Valid SSL certificate

## 📊 Optional Enhancements

- [ ] **Custom domain configured**
  - Vercel Dashboard → Settings → Domains
  - Add: `yourdomain.com`

- [ ] **Analytics enabled**
  - Vercel Dashboard → Analytics
  - Enable Vercel Analytics

- [ ] **Monitoring set up**
  - Consider: Sentry, LogRocket, Datadog

- [ ] **Database migrated** (if needed)
  - SQLite → Vercel Postgres
  - Or external DB (Neon, Supabase)

## 🔄 Continuous Deployment

- [ ] **Auto-deploy configured**
  - Push to GitHub → Auto deploys
  - Pull requests → Preview deployments

- [ ] **Deployment notifications**
  - Vercel → Settings → Notifications
  - Enable: Slack, Discord, Email

## 📝 Documentation

- [ ] **Updated README.md**
  - Add deployment URL
  - Add "Deploy to Vercel" button

- [ ] **Team notified**
  - Share deployment URL
  - Share access to Vercel project

- [ ] **Backup created**
  - Environment variables documented
  - Database backup (if applicable)

## 🎉 Launch

- [ ] **Production ready**
  - All checks passed
  - Users can access app
  - Monitoring in place

- [ ] **Celebrate!** 🚀

---

## 📞 Need Help?

If any step fails, check:
1. **Vercel Logs:** Dashboard → Deployments → Function Logs
2. **[DEPLOYMENT.md](DEPLOYMENT.md):** Detailed troubleshooting
3. **Vercel Support:** https://vercel.com/support

---

## 🔐 Security Reminder

✅ API keys are:
- Encrypted in Vercel
- Never exposed to browser
- Only accessible to backend functions
- Can be rotated anytime

❌ Never:
- Commit .env to git
- Share API keys in chat/email
- Hardcode keys in code
- Expose keys in frontend

---

**Deployment Status:** [ ] Not Started  [ ] In Progress  [ ] Complete

**Deployment URL:** _______________________________________

**Date Deployed:** _______________________________________

**Deployed By:** _______________________________________
