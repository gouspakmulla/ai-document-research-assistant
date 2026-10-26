# Click-by-Click Production Deployment Guide
## AI Document Research Assistant (Frontend & Backend)

This guide provides **exact, click-by-click instructions** on how to deploy this project to production:
- **Database & Storage**: [Supabase](https://supabase.com) (PostgreSQL + `pgvector` + private PDF storage bucket)
- **Backend API**: [Render](https://render.com) (FastAPI + Python 3.11/3.12)
- **Frontend App**: [Vercel](https://vercel.com) (React 19 + TypeScript + Vite)

---

## Table of Contents
1. [Overview & Prerequisites](#1-overview--prerequisites)
2. [Step 1: Generate Security Keys Locally](#step-1-generate-security-keys-locally)
3. [Step 2: Configure Supabase (Database & Storage)](#step-2-configure-supabase-database--storage)
4. [Step 3: Deploy Backend on Render](#step-3-deploy-backend-on-render)
5. [Step 4: Deploy Frontend on Vercel](#step-4-deploy-frontend-on-vercel)
6. [Step 5: Link Frontend & Backend (CORS & Cookies)](#step-5-link-frontend--backend-cors--cookies)
7. [Step 6: Step-by-Step Verification Checklist](#step-6-step-by-step-verification-checklist)
8. [Troubleshooting & Common Pitfalls](#troubleshooting--common-pitfalls)

---

## 1. Overview & Prerequisites

Before starting, ensure you have active accounts on:
1. **GitHub**: Repository pushed at `https://github.com/gouspakmulla/ai-document-research-assistant`
2. **Supabase**: [supabase.com](https://supabase.com) (Project: `ai-document-research-assistant`, Ref: `orugyjoulnlqkwvhdapa`)
3. **Render**: [render.com](https://render.com) (Free account)
4. **Vercel**: [vercel.com](https://vercel.com) (Free account)

---

## Step 1: Generate Security Keys Locally

You need two 32-byte cryptographically secure random hexadecimal strings for session token encryption and CSRF protection.

1. Open PowerShell or Command Prompt on your computer.
2. Run this command:
   ```powershell
   python -c "import secrets; print('SECRET_KEY=' + secrets.token_hex(32)); print('CSRF_SECRET=' + secrets.token_hex(32))"
   ```
3. Copy the output values to a temporary notepad file. You will paste these into Render in Step 3.

---

## Step 2: Configure Supabase (Database & Storage)

### 2.1 Get the Async Database Connection String
1. Log into your [Supabase Dashboard](https://supabase.com/dashboard).
2. Click on your project: **`ai-document-research-assistant`** (`orugyjoulnlqkwvhdapa`).
3. In the left navigation menu, click the **Gear Icon (Project Settings)** at the bottom.
4. In the settings submenu, click **Database**.
5. Scroll down to the **Connection String** box.
6. Click the **URI** tab.
7. Under "Connection type", choose **Transaction Pooler** (recommended for serverless/container apps on port `6543`) or **Session Pooler** (port `5432`).
8. Copy the connection string provided. It looks like this:
   ```text
   postgresql://postgres.orugyjoulnlqkwvhdapa:[YOUR-PASSWORD]@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres
   ```
9. **CRITICAL EDIT**:
   - Change `postgresql://` at the start to **`postgresql+asyncpg://`**
   - Replace `[YOUR-PASSWORD]` with your actual Supabase database password.
   - Append `?ssl=require` at the end.
   - **Your final connection string must look like this:**
     ```text
     postgresql+asyncpg://postgres.orugyjoulnlqkwvhdapa:YourActualPassword@aws-0-ap-southeast-2.pooler.supabase.com:6543/postgres?ssl=require
     ```
   *(Save this string to your notepad for Step 3).*

---

### 2.2 Create the Private PDF Storage Bucket
Because Render containers destroy local files on restart, PDF files are stored in a private Supabase Storage bucket.

1. In the Supabase left navigation bar, click the **Storage** icon (folder icon).
2. Click the **New bucket** button (top right).
3. Fill out the dialog:
   - **Bucket name**: Type exactly: `documents`
   - **Public bucket**: **Toggle OFF / Disabled** (Keep it private so unauthorized users cannot access files).
   - Click **Restrict MIME types** and type: `application/pdf`
   - **Maximum file size limit**: Enter `25` MB (or `26214400` bytes).
4. Click **Save bucket**.

---

### 2.3 Retrieve Supabase Project URL & Service-Role Key
1. In the Supabase left navigation bar, click **Project Settings** (Gear icon) -> click **API**.
2. Locate **Project URL**:
   - Copy the URL (e.g., `https://orugyjoulnlqkwvhdapa.supabase.co`).
3. Locate **Project API keys**:
   - Look for the key labeled **`service_role`** (tagged with `secret`).
   - Click **Reveal**.
   - Copy the long secret key token.
   *(Save this to your notepad. Never share this key or expose it in frontend code).*

---

## Step 3: Deploy Backend on Render

### 3.1 Create Web Service
1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click the blue **New +** button in the top navbar -> select **Web Service**.
3. Under "Connect a repository", select your GitHub account and choose **`gouspakmulla/ai-document-research-assistant`**. Click **Connect**.
4. Fill in the service configuration fields:

| Field Name | What to Enter / Select |
| :--- | :--- |
| **Name** | `ai-document-research-backend` |
| **Region** | Select **Singapore** (closest to Supabase `ap-southeast-2` Oceania region) |
| **Branch** | `main` (or `master`, whichever is your primary branch on GitHub) |
| **Root Directory** | *(Leave completely empty / blank)* |
| **Runtime** | Select **Python 3** |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT --workers 2` |
| **Instance Type** | Select **Free** |

---

### 3.2 Configure Advanced Settings (Migrations & Health Check)
1. On the same page, scroll down and click **Advanced** button to expand it.
2. In the **Pre-Deploy Command** field, enter:
   ```bash
   alembic -c backend/alembic.ini upgrade head
   ```
   *(This automatically creates the `vector` extension, all database tables, and performance indexes before your backend accepts traffic).*
3. In the **Health Check Path** field, enter:
   ```text
   /api/v1/health
   ```
4. Leave **Auto-Deploy** set to **Yes**.

---

### 3.3 Add Backend Environment Variables
In the **Environment Variables** section on the same page, click **Add Environment Variable** for each of the following:

| Key | Value | Description |
| :--- | :--- | :--- |
| `PYTHON_VERSION` | `3.11.9` | Ensures exact Python runtime |
| `ENVIRONMENT` | `production` | Enables strict security & CSRF validation |
| `DEBUG` | `false` | Disables debug traces |
| `SECRET_KEY` | *(Paste 32-byte hex key from Step 1)* | JWT session signing secret |
| `CSRF_SECRET` | *(Paste 32-byte hex key from Step 1)* | CSRF token secret |
| `COOKIE_SECURE` | `true` | Enforces HTTPS-only cookies |
| `COOKIE_SAMESITE` | `none` | Required for cross-domain cookies between Vercel & Render |
| `DATABASE_URL` | *(Paste edited URL from Step 2.1)* | `postgresql+asyncpg://...` connection string |
| `STORAGE_BACKEND` | `supabase` | Routes PDF file uploads to Supabase Storage |
| `SUPABASE_URL` | *(Paste URL from Step 2.3)* | `https://orugyjoulnlqkwvhdapa.supabase.co` |
| `SUPABASE_SERVICE_ROLE_KEY` | *(Paste secret key from Step 2.3)* | Supabase administrative storage access key |
| `SUPABASE_STORAGE_BUCKET` | `documents` | Name of the bucket created in Step 2.2 |
| `CORS_ALLOWED_ORIGINS` | `http://localhost:5173` | Temporary until Vercel URL is ready in Step 5 |
| `EMBEDDING_PROVIDER` | `mock` | Default free test mode (or change to `openai` / `gemini`) |
| `LLM_PROVIDER` | `mock` | Default free test mode (or change to `openai` / `gemini`) |

> **Using Real OpenAI or Gemini?**
> - For OpenAI: set `EMBEDDING_PROVIDER=openai`, `LLM_PROVIDER=openai`, and add `OPENAI_API_KEY=sk-...`
> - For Gemini: set `EMBEDDING_PROVIDER=gemini`, `LLM_PROVIDER=gemini`, and add `GEMINI_API_KEY=AIzaSy...`

---

### 3.4 Deploy & Verify Backend
1. Click **Create Web Service** at the bottom of the page.
2. Render will start building the service:
   - It will install dependencies (`pip install`).
   - It will run the database migration (`alembic upgrade head`).
   - It will start the Uvicorn server.
3. Once the status shows **Live** (green dot), copy your public backend URL from the top left of the Render dashboard:
   - Example: `https://ai-document-research-backend.onrender.com`
4. **Test Backend in Your Browser**:
   - Open: `https://ai-document-research-backend.onrender.com/health`
     - Should return: `{"status":"healthy","service":"AI Document Research Assistant"}`
   - Open: `https://ai-document-research-backend.onrender.com/ready`
     - Should return: `{"status":"ready","database":"connected"}`

---

## Step 4: Deploy Frontend on Vercel

### 4.1 Import Project into Vercel
1. Log into your [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** (button in top right) -> select **Project**.
3. Under "Import Git Repository", find **`gouspakmulla/ai-document-research-assistant`** and click **Import**.

---

### 4.2 Configure Project Settings
On the "Configure Project" screen:
1. **Project Name**: `ai-document-research-assistant` (or leave default).
2. **Framework Preset**: Verify it says **`Vite`**.
3. **Root Directory**:
   - Click the **Edit** button next to Root Directory.
   - Select the **`frontend`** folder.
   - Click **Continue**.
4. **Build and Output Settings**:
   - Leave defaults as-is:
     - Build Command: `npm run build`
     - Output Directory: `dist`
     - Install Command: `npm install`

---

### 4.3 Add Frontend Environment Variable
Expand the **Environment Variables** section:
1. In the **Key** field, enter:
   ```text
   VITE_API_URL
   ```
2. In the **Value** field, enter your Render backend URL followed by `/api/v1` **(Do NOT add a trailing slash)**:
   ```text
   https://ai-document-research-backend.onrender.com/api/v1
   ```
   *(Replace with your actual Render URL from Step 3.4).*
3. Click **Add**.

---

### 4.4 Deploy Frontend
1. Click the blue **Deploy** button.
2. Wait 1 to 2 minutes for Vercel to install packages, compile TypeScript, and build Vite assets.
3. Once completed, Vercel will show a celebration screen with your live URL:
   - Example: `https://ai-document-research-assistant.vercel.app`
4. Copy this live frontend URL.

---

## Step 5: Link Frontend & Backend (CORS & Cookies)

Because the frontend is on `*.vercel.app` and the backend is on `*.onrender.com`, modern browsers require explicit permission to send authenticated cookies across domains.

1. Go back to your [Render Dashboard](https://dashboard.render.com).
2. Click on your backend service: **`ai-document-research-backend`**.
3. In the left navigation menu, click **Environment**.
4. Find the variable **`CORS_ALLOWED_ORIGINS`**.
5. Click the edit icon (pencil) and update its value to your exact Vercel URL (no trailing slash):
   ```text
   https://ai-document-research-assistant.vercel.app
   ```
6. Double-check that these two cookie variables are present:
   - `COOKIE_SECURE` = `true`
   - `COOKIE_SAMESITE` = `none`
7. Click **Save Changes**.
8. Render will trigger a quick zero-downtime redeployment with the updated settings.

---

## Step 6: Step-by-Step Verification Checklist

Open your live Vercel frontend URL (`https://ai-document-research-assistant.vercel.app`) and execute this test plan:

### 1. User Registration & Authentication
- [ ] Click **Sign Up** / **Register**.
- [ ] Create a new account with an email and password.
- [ ] Verify you are logged in and redirected to the **Dashboard**.
- [ ] Press `F12` to open DevTools -> Go to **Application** tab -> **Cookies**:
  - Verify `doc_assistant_session` is stored.
  - Verify `HttpOnly` is checked.
  - Verify `Secure` is checked.
  - Verify `SameSite` is `None`.

### 2. Document Upload & Storage Verification
- [ ] In the dashboard, click **Upload PDF**.
- [ ] Select a sample research or documentation PDF (under 25MB).
- [ ] Watch the processing badge transition from `INDEXING` &rarr; `READY`.
- [ ] Open your [Supabase Dashboard](https://supabase.com/dashboard) -> **Storage** -> `documents` bucket.
  - Verify a new PDF file exists under a subfolder named with your user ID: `<user_id>/<file_uuid>.pdf`.

### 3. PDF In-Browser Viewing
- [ ] In the web app, click on the uploaded document name.
- [ ] Verify the PDF Viewer opens and renders the PDF pages smoothly without errors.

### 4. Conversational RAG & Citations
- [ ] Navigate to the **Workspace** / **Chat** page.
- [ ] Select your uploaded document in the document selector.
- [ ] Ask a question directly related to the PDF's content.
- [ ] Verify the assistant answers with grounded information and includes clickable page citation pills.
- [ ] Click a citation pill and verify the PDF viewer jumps directly to the cited page.

---

## Troubleshooting & Common Pitfalls

### 1. Backend error: `NoSuchModuleError: Can't load plugin: sqlalchemy.dialects:postgresql`
- **Cause**: The connection string in `DATABASE_URL` starts with `postgresql://` instead of `postgresql+asyncpg://`.
- **Fix**: In Render -> Environment -> `DATABASE_URL`, change the prefix to `postgresql+asyncpg://`.

### 2. Render Free Tier Sleep / Cold Starts
- **Behavior**: On Render Free tier, the backend sleeps if no traffic is received for 15 minutes. When you open the frontend after a while, the first request may take 50–60 seconds to wake up the server.
- **Fix**: Wait 60 seconds on the first load. To eliminate sleep, upgrade to Render Starter ($7/mo) or configure a free ping service (like UptimeRobot) to send a GET request to `https://<backend-url>/health` every 10 minutes.

### 3. User Automatically Logs Out Upon Page Refresh
- **Cause**: Cross-domain cookies are blocked by the browser because `COOKIE_SAMESITE` is set to `lax` or `COOKIE_SECURE` is `false`.
- **Fix**: In Render -> Environment:
  - Set `COOKIE_SAMESITE` to `none`
  - Set `COOKIE_SECURE` to `true`
  - Ensure `CORS_ALLOWED_ORIGINS` matches the exact frontend URL.

### 4. CORS Error in Browser Console (`Access-Control-Allow-Origin`)
- **Cause**: `CORS_ALLOWED_ORIGINS` has a trailing slash (e.g. `https://my-app.vercel.app/`).
- **Fix**: Remove trailing slashes: `https://my-app.vercel.app`. Note that the backend also automatically accepts all `https://*.vercel.app` preview domains via regular expression.

### 5. Document Upload Returns 500
- **Cause**: Supabase Storage credentials are missing or the bucket name does not match.
- **Fix**: In Render -> Environment:
  - Confirm `STORAGE_BACKEND` is set to `supabase`
  - Confirm `SUPABASE_STORAGE_BUCKET` is set to `documents`
  - Confirm `SUPABASE_SERVICE_ROLE_KEY` is the secret `service_role` key from Supabase (not the `anon` key).
