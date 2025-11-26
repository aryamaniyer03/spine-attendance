# Spine Attendance Automation - Render Deployment

Flask API deployed on Render.com that automates clock-in and clock-out for Spine HR system using Selenium.

## 🚀 Quick Deploy to Render

### Option 1: Deploy via GitHub (Recommended)

1. **Create a GitHub repository:**
   - Go to https://github.com/new
   - Create a new repository (e.g., `spine-attendance`)
   - Don't initialize with README

2. **Push this code to GitHub:**
   ```bash
   cd "C:\Users\sowilo.in1\Documents\Spine\render-deployment"
   git init
   git add .
   git commit -m "Initial commit"
   git branch -M main
   git remote add origin https://github.com/YOUR_USERNAME/spine-attendance.git
   git push -u origin main
   ```

3. **Deploy on Render:**
   - Go to https://dashboard.render.com/
   - Sign up/Login (use GitHub to sign in)
   - Click "New +" → "Web Service"
   - Connect your GitHub repository
   - Render will auto-detect the Dockerfile
   - Click "Create Web Service"
   - Wait 5-10 minutes for deployment

### Option 2: Deploy via Render Dashboard (Manual)

1. **Create a new Web Service:**
   - Go to https://dashboard.render.com/
   - Click "New +" → "Web Service"
   - Choose "Deploy an existing image from a registry" OR "Build and deploy from a Git repository"

2. **Configure the service:**
   - **Name:** spine-attendance
   - **Region:** Singapore
   - **Runtime:** Docker
   - **Plan:** Free

3. **Set Environment Variables:**
   Go to Environment tab and add:
   ```
   SPINE_URL=https://msowinv.spinehrm.in/login.aspx?ReturnUrl=%2fhomepage.aspx
   SPINE_USERNAME=SIE014
   SPINE_PASSWORD=@Yer2oo3
   CHROMEDRIVER_PATH=/usr/local/bin/chromedriver
   PORT=10000
   ```

4. **Deploy:**
   - Click "Create Web Service"
   - Wait for deployment (5-10 minutes)

## 📡 API Endpoints

Once deployed, your app will be available at: `https://spine-attendance.onrender.com`

### Available Endpoints:

- **GET /** - Status page
  ```bash
  curl https://spine-attendance.onrender.com/
  ```

- **GET /health** - Health check
  ```bash
  curl https://spine-attendance.onrender.com/health
  ```

- **GET /clock-in** - Trigger clock-in
  ```bash
  curl https://spine-attendance.onrender.com/clock-in
  ```

- **GET /clock-out** - Trigger clock-out
  ```bash
  curl https://spine-attendance.onrender.com/clock-out
  ```

## ⏰ Scheduled Clock-In/Clock-Out

Render free tier spins down after 15 minutes of inactivity. Use an external cron service:

### Option 1: cron-job.org (Free, Recommended)

1. Go to https://cron-job.org
2. Sign up for free
3. Create new cron jobs:
   - **Clock-in at 8:45 AM IST (3:15 AM UTC):**
     - URL: `https://spine-attendance.onrender.com/clock-in`
     - Schedule: `15 3 * * 1-5` (Mon-Fri)

   - **Clock-out at 6:00 PM IST (12:30 PM UTC):**
     - URL: `https://spine-attendance.onrender.com/clock-out`
     - Schedule: `30 12 * * 1-5` (Mon-Fri)

### Option 2: GitHub Actions (Free)

Create `.github/workflows/attendance.yml` in your repository:

```yaml
name: Attendance Automation

on:
  schedule:
    # Clock-in at 3:15 AM UTC (8:45 AM IST)
    - cron: '15 3 * * 1-5'
    # Clock-out at 12:30 PM UTC (6:00 PM IST)
    - cron: '30 12 * * 1-5'
  workflow_dispatch:  # Allow manual trigger

jobs:
  clock-in:
    runs-on: ubuntu-latest
    if: github.event.schedule == '15 3 * * 1-5' || github.event_name == 'workflow_dispatch'
    steps:
      - name: Trigger Clock-In
        run: curl https://spine-attendance.onrender.com/clock-in

  clock-out:
    runs-on: ubuntu-latest
    if: github.event.schedule == '30 12 * * 1-5' || github.event_name == 'workflow_dispatch'
    steps:
      - name: Trigger Clock-Out
        run: curl https://spine-attendance.onrender.com/clock-out
```

## 💰 Cost

**100% FREE** with Render's free tier:
- 750 hours/month (enough for 24/7 uptime)
- Automatic HTTPS
- Auto-deploy from GitHub
- **Limitation:** Spins down after 15 min inactivity (solved with cron jobs)

## 🔄 Updates

To update your deployed app:

1. **Make changes locally**
2. **Push to GitHub:**
   ```bash
   cd "C:\Users\sowilo.in1\Documents\Spine\render-deployment"
   git add .
   git commit -m "Update"
   git push
   ```
3. **Render auto-deploys** (if you enabled auto-deploy)

## 📊 Monitoring

- **View logs:** https://dashboard.render.com → Your Service → Logs
- **View metrics:** Dashboard shows CPU, Memory, Response times
- **Health checks:** Render automatically monitors `/health` endpoint

## 🛠️ Troubleshooting

### Service keeps spinning down:
- Set up external cron jobs to ping your service regularly
- Upgrade to paid plan ($7/month) for always-on service

### Chrome/ChromeDriver errors:
- Check logs in Render dashboard
- Verify Dockerfile includes all Chrome dependencies

### Timeout errors:
- Selenium operations take 30-60 seconds
- Render free tier has 60s timeout (should be fine)

## 📝 Files Included

- `Dockerfile` - Container setup with Chrome + Selenium
- `app.py` - Flask API server
- `render.yaml` - Render configuration (auto-deployment)
- `requirements.txt` - Python dependencies
- `automation.py` - Main automation facade
- `automation_orchestrator.py` - Flow coordinator
- `automation_shared.py` - Shared Selenium utilities
- `automation_flows/` - Clock-in/out logic
- `.env` - Environment variables (not committed to Git)

## 🔒 Security Notes

- Store credentials as Render Environment Variables (encrypted)
- Never commit `.env` file to version control
- HTTPS is enforced automatically
- Environment variables are injected at runtime

## 📞 Support

For Render issues:
- Docs: https://render.com/docs
- Community: https://community.render.com/

## 🎯 Next Steps After Deployment

1. Test the endpoints manually
2. Set up cron jobs for automation
3. Monitor logs for first few runs
4. Add error notifications (optional - via email/Telegram)
