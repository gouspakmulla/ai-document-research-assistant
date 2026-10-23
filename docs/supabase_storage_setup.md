# Persistent PDF Storage Integration Guide (Supabase Storage)

This guide documents the persistent storage architecture, exact required environment variables, and manual Supabase dashboard configuration for the **AI Document Research Assistant** (Phase 9).

---

## 1. Storage Architecture Overview

The backend uses a provider-agnostic storage abstraction (`StorageService`) allowing seamless switching between local disk storage (for offline development) and cloud-native **Supabase Storage** (for production):

```
+-------------------------------------------------------------------------+
|                              FastAPI Backend                            |
|                                                                         |
|  +--------------------+         +------------------------------------+  |
|  |  DocumentService   | ------> |           StorageService           |  |
|  +--------------------+         +------------------------------------+  |
|                                       |                      |          |
|                                       v                      v          |
|                             LocalStorageProvider   SupabaseStorageProvider
+-------------------------------------------------------------|-----------+
                                                              |
                                                    Server-Side HTTPS
                                                    (Service-Role Key)
                                                              |
                                                              v
                                                +---------------------------+
                                                |  Supabase Storage (Cloud) |
                                                |  Private Bucket:          |
                                                |  `documents`              |
                                                |  Path: {user_id}/{id}.pdf |
                                                +---------------------------+
```

### Key Security & Isolation Guarantees:
1. **Server-Side Credentials Only**:
   - The Supabase Service-Role key (`SUPABASE_SERVICE_ROLE_KEY`) is stored **strictly on the backend server**.
   - It is **never** sent to the client browser, injected into Vite bundles, or included in client-side code.
2. **Private Bucket**:
   - The bucket `documents` is marked **Private** (`public = false`).
   - Direct anonymous or unauthorized requests from the internet will receive `400/403/404` errors.
3. **Strict Backend Tenant Isolation**:
   - Object paths are strictly partitioned per tenant: `{user_id}/{unique_file_uuid}.pdf`.
   - The backend validates session authentication and checks tenant ownership (`user_id == current_user.id`) in PostgreSQL before performing any upload, download stream, chunk query, or deletion.
4. **Content Validation**:
   - Strict validation of `%PDF-` magic header bytes, `.pdf` extension, MIME types, and file size limit (25MB) prior to storage persistence.
5. **Backwards Compatibility**:
   - Existing documents and files in `backend/storage/documents/` remain completely intact.
   - When retrieving documents, `StorageService` automatically checks local disk if a document record references a local file.

---

## 2. Environment Variables Specification

The following variables configure persistent storage in `.env`:

| Variable Name | Required | Default | Description |
| :--- | :--- | :--- | :--- |
| `STORAGE_BACKEND` | Yes | `local` | Active storage provider: `local` (disk), `supabase` (cloud), or `mock` (unit tests). |
| `STORAGE_DIR` | For `local` | `backend/storage/documents` | Directory path on local disk for local development. |
| `MAX_FILE_SIZE_MB` | No | `25` | Maximum allowed PDF size in megabytes. |
| `ALLOWED_EXTENSIONS` | No | `.pdf` | Allowed file extensions. |
| `ALLOWED_MIME_TYPES` | No | `application/pdf` | Allowed MIME content types. |
| `SUPABASE_URL` | For `supabase` | `None` | Supabase Project URL (e.g., `https://<project-ref>.supabase.co`). |
| `SUPABASE_SERVICE_ROLE_KEY` | For `supabase` | `None` | Supabase **service_role** secret API key with administrative bucket access. |
| `SUPABASE_STORAGE_BUCKET` | No | `documents` | Name of the private Supabase storage bucket. |
| `SUPABASE_STORAGE_TIMEOUT_SECONDS` | No | `30.0` | HTTP request timeout in seconds for Supabase Storage API calls. |

> [!WARNING]
> **NEVER expose `SUPABASE_SERVICE_ROLE_KEY`**:
> Do not prefix this key with `VITE_` or include it in `frontend/.env`. This key grants administrative access to storage and database functions and must reside solely in the server `.env`.

---

## 3. Step-by-Step Manual Supabase Dashboard Setup

Follow these exact steps in your Supabase project dashboard to set up the private bucket:

### Step 3.1: Create the Private Storage Bucket
1. Log in to the [Supabase Dashboard](https://supabase.com/dashboard).
2. Select your project.
3. In the left navigation menu, click on **Storage** (folder icon).
4. Click **New bucket** (top right of the Storage panel).
5. Configure the bucket settings:
   - **Bucket name**: `documents`
   - **Public bucket**: **Toggle OFF (Disabled)** *(Crucial: Ensures bucket is strictly private)*
   - **Allowed MIME types**: Click **Restrict MIME types** and enter:
     ```
     application/pdf
     ```
   - **Maximum file size limit**: Enter `25` MB (or `26214400` bytes).
6. Click **Save bucket**.

### Step 3.2: Retrieve Server-Side Project Credentials
1. In the left sidebar, click **Project Settings** (gear icon at the bottom).
2. Click **API** under Configuration.
3. Locate the **Project URL**:
   - Copy the URL (format: `https://<project-id>.supabase.co`).
   - Assign this value to `SUPABASE_URL` in your backend `.env`.
4. Under **Project API keys**, locate the **service_role** key:
   - Note: This key has the tag `secret` / `service_role`.
   - Click **Reveal** and copy the secret key.
   - Assign this value to `SUPABASE_SERVICE_ROLE_KEY` in your backend `.env`.

> [!IMPORTANT]
> The `anon` / `public` key is **not** sufficient for private bucket management without RLS token exchange. Using the `service_role` key server-side ensures the backend can safely store and retrieve user PDFs while enforcing tenant isolation through FastAPI auth session cookies and PostgreSQL database checks.

### Step 3.3: Storage RLS Policies (Optional Defense-in-Depth)
Because the backend connects via the service-role key, requests bypass Storage RLS by default. If you wish to enable additional defense-in-depth:
- Keep the bucket private.
- Since clients do not connect directly to Supabase Storage, no public read/write policies are needed or recommended.

---

## 4. Local vs. Production Switching

### For Local Offline Development:
In your backend `.env`:
```bash
STORAGE_BACKEND=local
STORAGE_DIR=backend/storage/documents
```
PDFs will be stored on local disk under `backend/storage/documents/`. Existing files and tests run without any external internet connection or cloud service dependencies.

### For Production / Supabase Persistent Storage:
In your deployment environment or backend `.env`:
```bash
STORAGE_BACKEND=supabase
SUPABASE_URL=https://<your-project-id>.supabase.co
SUPABASE_SERVICE_ROLE_KEY=<your-service-role-secret-key>
SUPABASE_STORAGE_BUCKET=documents
SUPABASE_STORAGE_TIMEOUT_SECONDS=30.0
```

---

## 5. Verification & Health Check Procedure

Once you have configured the environment variables, verify the integration:

1. **Run Storage Integration Tests**:
   ```bash
   .venv\Scripts\pytest backend\tests\test_storage.py -v
   ```
   All 17 tests should pass.

2. **Verify Backward Compatibility**:
   Ensure existing documents stored on disk continue to stream correctly:
   ```bash
   .venv\Scripts\pytest backend\tests\test_documents.py -v
   ```

3. **Manual Upload Verification via Web UI**:
   - Start the backend: `uvicorn backend.app.main:app --reload`
   - Start the frontend: `npm run dev`
   - Log into the app, navigate to **Document Library**, and click **Upload PDF**.
   - Upload a test document.
   - In the Supabase Dashboard -> **Storage** -> `documents`, verify that a new object appears under `<user_id>/<uuid>.pdf`.
   - In the Web UI, open the document in the PDF Viewer and verify pages render and chunks are cited in chat.
   - Delete the document in the Web UI and verify the object is removed from Supabase Storage.
