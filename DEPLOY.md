# Deployment Guide

Deploy Quant Poker Edge for 24/7 mobile access.

---

## Option 1: Streamlit Community Cloud (Free & Easiest)

**Best for:** Quick deployment, public apps, no server management.

### Prerequisites
- GitHub account
- Repository pushed to GitHub (already done)

### Steps

1. **Go to Streamlit Cloud**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Sign in with GitHub

2. **Deploy the App**
   - Click **"New app"**
   - Select your repository: `willhammondhimself/poker-tracker`
   - Branch: `main`
   - Main file path: `app.py`
   - Click **"Deploy"**

3. **Configure Secrets (API Key)**
   - After deployment, go to app settings (⚙️ icon)
   - Click **"Secrets"**
   - Add your Perplexity API key:
   ```toml
   [perplexity]
   api_key = "pplx-your-api-key-here"
   ```
   - Click **"Save"**

4. **Access Your App**
   - URL format: `https://your-app-name.streamlit.app`
   - Bookmark on your phone for quick access

### Limitations
- **Data Persistence:** Data resets on app restart (JSON files are ephemeral)
- **Cold Starts:** App may take 10-30s to wake if idle
- **Public URL:** Anyone with the link can access (no auth by default)

### Adding Basic Auth (Optional)
Add to your secrets:
```toml
[passwords]
admin = "your-password-here"
```

Then add to `app.py` at the top of `main()`:
```python
def check_password():
    password = st.text_input("Password", type="password")
    if password == st.secrets.get("passwords", {}).get("admin"):
        return True
    return False

if not check_password():
    st.stop()
```

---

## Option 2: Render (More Robust)

**Best for:** Persistent data, private apps, more control.

### Prerequisites
- Render account ([render.com](https://render.com))
- GitHub repo connected

### Steps

1. **Create New Web Service**
   - Go to Render Dashboard → **"New +"** → **"Web Service"**
   - Connect your GitHub repo
   - Name: `quant-poker-edge`

2. **Configure Build Settings**
   ```
   Environment: Python 3
   Build Command: pip install -r requirements.txt
   Start Command: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```

3. **Add Environment Variables**
   - Go to **"Environment"** tab
   - Add secret:
     - Key: `PERPLEXITY_API_KEY`
     - Value: `pplx-your-api-key-here`

4. **Update Code for Render Secrets**
   In `utils/ai_coach.py`, update `get_api_key()`:
   ```python
   import os

   def get_api_key() -> Optional[str]:
       # Try environment variable first (for Render/Railway)
       env_key = os.environ.get("PERPLEXITY_API_KEY")
       if env_key:
           return env_key

       # Try Streamlit secrets
       try:
           return st.secrets.get("perplexity", {}).get("api_key")
       except Exception:
           pass

       return st.session_state.get("perplexity_api_key")
   ```

5. **Persistent Storage (Optional)**
   - Render offers persistent disks ($0.25/GB/month)
   - Attach to `/app/data` for session/hand data persistence

### Pricing
- **Free tier:** 750 hours/month, sleeps after 15 min inactivity
- **Starter ($7/mo):** Always on, no sleep

---

## Option 3: Railway (Alternative)

**Best for:** Simple deploys, good free tier, easy scaling.

### Steps

1. **Create Railway Account**
   - Visit [railway.app](https://railway.app)
   - Sign in with GitHub

2. **Deploy from GitHub**
   - Click **"New Project"** → **"Deploy from GitHub repo"**
   - Select `poker-tracker` repository

3. **Configure**
   - Railway auto-detects Python
   - Add environment variable:
     - `PERPLEXITY_API_KEY` = your key

4. **Add Procfile** (create in repo root):
   ```
   web: streamlit run app.py --server.port $PORT --server.address 0.0.0.0
   ```

5. **Deploy**
   - Railway auto-deploys on git push
   - Access via generated URL

### Pricing
- **Free tier:** $5 credit/month (~500 hours)
- **Hobby ($5/mo):** More resources, custom domains

---

## Quick Comparison

| Feature | Streamlit Cloud | Render | Railway |
|---------|----------------|--------|---------|
| **Cost** | Free | Free / $7+ | Free / $5+ |
| **Setup Time** | 2 min | 10 min | 5 min |
| **Data Persistence** | ❌ Ephemeral | ✅ Disk option | ✅ Volumes |
| **Custom Domain** | ❌ | ✅ | ✅ |
| **Cold Starts** | Yes (slow) | Yes (free) | Yes (free) |
| **Auth** | Manual | Built-in | Built-in |

---

## Recommended for You

**Start with Streamlit Cloud** - it's free, takes 2 minutes, and works great for personal use. Your session data resets periodically, but you can always export important data.

If you want persistent data and more control, upgrade to **Render Starter ($7/mo)** later.

---

## Mobile Access Tips

1. **Add to Home Screen (iOS)**
   - Open your deployed app URL in Safari
   - Tap Share → "Add to Home Screen"
   - Now it opens like a native app

2. **Add to Home Screen (Android)**
   - Open in Chrome
   - Tap menu → "Add to Home screen"

3. **Bookmark for Quick Access**
   - Save URL to your browser favorites
   - Access instantly from any device

---

## Troubleshooting

### App Won't Start
- Check `requirements.txt` has all dependencies
- Verify `runtime.txt` specifies `python-3.9`
- Check logs in deployment platform dashboard

### API Key Not Working
- Verify key is correctly set in secrets/environment
- Check for extra spaces or quotes
- Test key works locally first

### Data Not Saving
- Streamlit Cloud: Expected behavior (ephemeral storage)
- Render/Railway: Ensure persistent disk is attached

---

## Files Required for Deployment

```
poker-tracker/
├── app.py              # Main application
├── requirements.txt    # Python dependencies
├── runtime.txt         # Python version (python-3.9)
├── .streamlit/
│   └── secrets.toml.example  # Template for secrets
├── components/         # UI components
├── utils/              # Backend utilities
└── data/               # JSON data files
```
