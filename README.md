# Pyxten - Phase 1 Zoning Validation System

Production-ready web application for Phase 1 zoning validation in Puerto Rico.

## Architecture

- **Frontend**: Next.js (App Router) with TypeScript + Tailwind CSS - deployed on Vercel
- **Backend API**: FastAPI (Python 3.11) - deployed on Railway
- **Auth + DB**: Supabase Auth + Supabase Postgres

## Project Structure

```
/api                    # FastAPI Backend
  /app
    /routers           # API endpoints (projects, validations, folders)
    /services          # Business logic (validation, PDF generation)
    main.py            # FastAPI application
    config.py          # Environment configuration
    models.py          # SQLAlchemy models
    schemas.py         # Pydantic schemas
    auth.py            # JWT authentication
  requirements.txt
  Procfile             # Railway deployment

/frontend              # Next.js Frontend
  /app                 # App Router pages
    /login             # Login page
    /signup            # Signup page
    /(app)             # Protected app routes
      /dashboard       # Main dashboard
      /nueva-validacion # New validation wizard
      /proyectos       # Projects list
      /folders/[id]    # Folder detail
  /components          # React components
  /lib                 # API client and utilities

/migrations            # SQL migrations
  001_folders_tables.sql  # Folders + RLS policies
```

## Setup Instructions

### 1. Supabase Setup

1. Create a new Supabase project at https://supabase.com

2. Run the base schema SQL in SQL Editor (from `supabase_setup.sql`):
   - Creates `projects`, `validations`, `usage_tracking` tables
   - Enables Row Level Security (RLS)
   - Creates indexes and triggers

3. Run the folders migration (from `migrations/001_folders_tables.sql`):
   - Creates `folders` and `folder_items` tables
   - Enables RLS policies for folders

4. Get your Supabase credentials from Project Settings:
   - `SUPABASE_URL`: Project URL
   - `SUPABASE_ANON_KEY`: anon/public key
   - `SUPABASE_JWT_SECRET`: JWT Secret (from API settings)
   - `DATABASE_URL`: Connection string (from Database settings)

### 2. External API Keys

- **Google Maps API Key**: Enable Geocoding API at https://console.cloud.google.com
- **Anthropic API Key**: Get from https://console.anthropic.com

### 3. Backend Deployment (Railway)

1. Create a new project on Railway: https://railway.app

2. Connect your GitHub repository or deploy the `/api` folder

3. Set environment variables:
   ```
   DATABASE_URL=postgresql://postgres:[PASSWORD]@db.[REF].supabase.co:5432/postgres
   SUPABASE_URL=https://[REF].supabase.co
   SUPABASE_JWT_SECRET=your-jwt-secret
   GOOGLE_MAPS_API_KEY=your-google-maps-key
   ANTHROPIC_API_KEY=your-anthropic-key
   CORS_ALLOWED_ORIGINS=https://your-app.vercel.app,http://localhost:3000
   ```

4. Railway will auto-detect the Procfile and deploy

5. Note your Railway API URL (e.g., `https://pyxten-api.up.railway.app`)

### 4. Frontend Deployment (Vercel)

1. Create a new project on Vercel: https://vercel.com

2. Connect your GitHub repository and set the root directory to `/frontend`

3. Set environment variables:
   ```
   NEXT_PUBLIC_SUPABASE_URL=https://[REF].supabase.co
   NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
   NEXT_PUBLIC_API_BASE_URL=https://your-api.railway.app
   ```

4. Deploy

### 5. Local Development

**Backend:**
```bash
cd api
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
cp .env.example .env
# Edit .env with your credentials
uvicorn app.main:app --reload
```

**Frontend:**
```bash
cd frontend
npm install
cp .env.local.example .env.local
# Edit .env.local with your credentials
npm run dev
```

## API Endpoints

### Projects
- `GET /projects` - List user's projects
- `POST /projects` - Create project
- `GET /projects/{id}` - Get project
- `PATCH /projects/{id}` - Update project
- `DELETE /projects/{id}` - Delete project
- `POST /projects/{id}/validate_fase1` - Run Phase 1 validation

### Validations
- `GET /validations` - List validations (optional `?project_id=`)
- `GET /validations/{id}` - Get validation detail
- `GET /validations/{id}/report.pdf` - Download PDF report

### Folders
- `GET /folders` - List folders
- `POST /folders` - Create folder
- `GET /folders/{id}` - Get folder
- `DELETE /folders/{id}` - Delete folder
- `GET /folders/{id}/items` - List folder items
- `POST /folders/{id}/items` - Add validation to folder
- `DELETE /folders/{id}/items/{item_id}` - Remove item from folder

## Phase 1 Validation Logic

The validation process:

1. **Geocoding**: Validates address with Google Maps API
2. **ArcGIS Lookup**: Queries MIPR for zoning district and overlays
3. **POT Equivalency**: Maps municipal POT codes to RC 2020 codes
4. **Use Classification**: Parses project description with Claude AI
5. **Compatibility Check**: Validates use against zoning rules
6. **Overlay Check**: Identifies additional restrictions (historic, coastal, flood)
7. **Result Generation**: Produces viability determination

## PDF Report Wording

Critical requirements for PDF generation:

- **If viable**: "El proyecto cumple con los requisitos de zonificacion en esa area."
- **If NOT viable**: "El uso propuesto no es compatible con la zonificacion."
- **REMOVED**: "Proximos Pasos recomendados" section is NOT included

## Database Notes

- **Municipality column**: NOT stored in `validations` table
- **Derived from projects**: Municipality is retrieved via JOIN with projects table
- **PGRST204 fix**: Do not insert `municipality` into validations

## RLS Security

All tables have Row Level Security enabled:
- Users can only see/modify their own data
- Policies enforce `auth.uid() = user_id` check
- Folders cascade delete to folder_items

## Consola del Revisor (Fase 1)

The reviewer console is the municipal side of the counter: a permit reviewer
opens a case, uploads the PDFs of a Permiso Unico package, and sees each one
classified. It lives alongside the applicant product and shares nothing with it
except the Next.js app shell and the FastAPI process.

### Setup

1. **Run the migrations, in order, in the Supabase SQL Editor:**
   - `migrations/004_documents_bucket_policies.sql` — storage policies for the
     now-private `documents` bucket. **Required for the existing applicant
     document upload to work.**
   - `migrations/005_reviewer_core.sql` — reviewer tables, RLS policies, the
     private `expedientes` bucket, and a seeded San Juan organization.

2. **Set the new backend environment variables** (Railway):
   ```
   SUPABASE_ANON_KEY=...      # required: RLS enforcement for reviewer routes
   ANTHROPIC_API_KEY=...      # required: document classification
   ```

3. **Grant a reviewer access.** They must have signed up first, then:
   ```sql
   SELECT public.reviewer_grant('persona@sanjuan.pr.gov', 'San Juan', 'reviewer');
   ```
   Roles: `intake`, `reviewer`, `supervisor`, `auditor`. An `auditor` can read
   everything and change nothing.

The console link appears in the sidebar only for users with a membership.
Everyone else gets a 403 from the API regardless of what they navigate to.

### How isolation works here

Applicant routes reach Postgres through SQLAlchemy as the `postgres` role, which
**bypasses Row Level Security** — isolation there is the `.filter(user_id == ...)`
in each handler.

Reviewer routes do not. They reach Postgres through PostgREST carrying the
caller's own JWT, so the `org_id` policies in migration 005 are what actually
prevents a reviewer in one municipality from reading another's case. A handler
that forgets to filter by org gets nothing back anyway.

### Rules that are enforced, not just documented

- **No finding without evidence.** `extracted_facts` has a CHECK constraint: a
  fact claiming `status = 'extraido'` must name a document and a page.
- **The audit trail is append-only.** Trigger plus `REVOKE UPDATE, DELETE`. There
  is no update function in `app/reviewer/audit.py` to call.
- **Cases are bound to a ruleset version.** `cases.ruleset_version_id` is frozen
  by trigger, so changing the rules never rewrites history.
- **No confidence percentages.** Bands are `alta` / `media` / `baja`, computed
  from signals we check ourselves (did two independent views agree? did the PDF
  carry text?) — never asked of the model.
- **Anthropic only on the reviewer path.** The applicant flow keeps its OpenAI
  calls; a test fails the build if the two ever mix.
- **Nothing is sent to an applicant.** There is no send path in this MVP.

Each of these has a test in `api/tests/test_guardrails.py`.

### Decision states

| Identificador | Texto en pantalla |
| --- | --- |
| `sin_hallazgos` | Sin hallazgos en las verificaciones cubiertas |
| `hallazgo_identificado` | Hallazgo identificado — ver evidencia |
| `requiere_criterio` | Requiere criterio del revisor |

These strings are fixed. Do not paraphrase them, and never render "COMPLIANT" or
"NON-COMPLIANT" anywhere in this product.

### Running the tests

```bash
cd api
pip install -r requirements.txt pytest
pytest
```

The suite covers the reviewer path and includes regression tests asserting that
every applicant route still exists and still requires authentication.

## Roadmap

- [x] Phase 1: Tomo 6 validation (Web App)
- [ ] Phase 2: Full PCOC validation
- [ ] Phase 3: Environmental compliance
- [ ] Phase 4: SBP integration
- [ ] Phase 5: Municipal expansion
- [x] Reviewer console Phase 1: case model + intake + document classification
- [ ] Reviewer console Phase 2: rules extracted to versioned tables, fact extraction, deterministic checks
- [ ] Reviewer console Phase 3: draft requerimiento de subsanacion

## License

Proprietary - All rights reserved
