# Pyxten Phase 1 - Test Checklist

## Pre-Deployment Verification

### Database Setup
- [ ] `supabase_setup.sql` executed successfully
- [ ] `migrations/001_folders_tables.sql` executed successfully
- [ ] RLS policies active on all tables

### Environment Variables
**Backend (Railway):**
- [ ] `DATABASE_URL` configured
- [ ] `SUPABASE_URL` configured
- [ ] `SUPABASE_JWT_SECRET` configured
- [ ] `GOOGLE_MAPS_API_KEY` configured
- [ ] `ANTHROPIC_API_KEY` configured
- [ ] `CORS_ALLOWED_ORIGINS` includes Vercel domain

**Frontend (Vercel):**
- [ ] `NEXT_PUBLIC_SUPABASE_URL` configured
- [ ] `NEXT_PUBLIC_SUPABASE_ANON_KEY` configured
- [ ] `NEXT_PUBLIC_API_BASE_URL` configured

---

## Functional Tests

### 1. User Authentication

#### Test 1.1: User Sign Up
- [ ] Navigate to `/signup`
- [ ] Enter email and password (min 6 characters)
- [ ] Click "Registrarse"
- [ ] Verify success message appears
- [ ] Check email for confirmation link

#### Test 1.2: User Login
- [ ] Navigate to `/login`
- [ ] Enter valid credentials
- [ ] Click "Iniciar Sesion"
- [ ] Verify redirect to `/dashboard`

#### Test 1.3: Sign Out
- [ ] Click "Cerrar Sesion" in sidebar
- [ ] Verify redirect to `/login`
- [ ] Verify cannot access `/dashboard` without login

---

### 2. Projects

#### Test 2.1: Create Project (via Nueva Validacion)
- [ ] Navigate to `/nueva-validacion`
- [ ] Select "Crear Nuevo Proyecto"
- [ ] Fill required fields:
  - Name: "Proyecto Prueba"
  - Address: "Calle Luna 123"
  - Municipality: "San Juan"
- [ ] Fill optional catastro field
- [ ] Verify disclaimer text appears under catastro input:
  "Debe verificar esta informacion para confirmar su exactitud."
- [ ] Add project description
- [ ] Click "Validar Proyecto"
- [ ] **VERIFY**: Project appears immediately in Proyectos list (no reload needed)

#### Test 2.2: List Projects
- [ ] Navigate to `/proyectos`
- [ ] Verify created project appears in table
- [ ] Verify all columns show correct data

#### Test 2.3: Delete Project
- [ ] Click "Eliminar" on a project
- [ ] Confirm deletion
- [ ] Verify project removed from list

---

### 3. Validations

#### Test 3.1: Run Phase 1 Validation
- [ ] Create or select a project with address and municipality
- [ ] Enter project description: "Quiero construir una residencia unifamiliar"
- [ ] Click "Validar Proyecto"
- [ ] Verify validation runs (may take 10-30 seconds)
- [ ] Verify result shows viable/not viable status
- [ ] Verify result shows zoning code and name

#### Test 3.2: Validation Appears on Dashboard
- [ ] Navigate to `/dashboard`
- [ ] Verify validation appears in "Validaciones Recientes"
- [ ] Verify columns show:
  - Project Name
  - Address
  - Municipality (from project JOIN)
  - Viable status
  - Date

#### Test 3.3: Download PDF Report
- [ ] Click "PDF" button on a validation
- [ ] Verify PDF opens/downloads
- [ ] **CRITICAL**: If viable, verify text:
  "El proyecto cumple con los requisitos de zonificacion en esa area."
- [ ] **CRITICAL**: If NOT viable, verify text:
  "El uso propuesto no es compatible con la zonificacion."
- [ ] **CRITICAL**: Verify "Proximos Pasos recomendados" section is NOT present

#### Test 3.4: Dashboard Search (Optional)
- [ ] Enter address substring in search box
- [ ] Verify table filters by address client-side

---

### 4. Folders

#### Test 4.1: Save Validation to New Folder
- [ ] On Dashboard, click "Guardar en Carpeta" for a validation
- [ ] Verify modal appears with:
  - Row 1: Dropdown for existing folders (blank if none)
  - Row 2: Text input for new folder name
  - Buttons: Cancelar / Guardar
- [ ] Enter new folder name: "Casa"
- [ ] Click "Guardar"
- [ ] Verify success message
- [ ] Verify folder appears under "Mis Proyectos"

#### Test 4.2: Save to Existing Folder
- [ ] Click "Guardar en Carpeta" for another validation
- [ ] Select existing folder "Casa" from dropdown
- [ ] Click "Guardar"
- [ ] Verify success message

#### Test 4.3: Duplicate Prevention
- [ ] Try to add the same validation to "Casa" folder again
- [ ] **VERIFY**: Error message appears: "Ya existe en la carpeta"
- [ ] Verify no duplicate row created

#### Test 4.4: Open Folder Detail
- [ ] Click on folder "Casa" under "Mis Proyectos"
- [ ] Verify navigates to `/folders/{id}`
- [ ] Verify folder name displays
- [ ] Verify items list shows:
  - Project Name
  - Address
  - Validation Date
  - Viable status
  - PDF button

#### Test 4.5: Empty Folder State
- [ ] Create a new empty folder
- [ ] Open folder detail
- [ ] **VERIFY**: Shows exactly: "No se ha seleccionado proyectos."

#### Test 4.6: Remove Item from Folder
- [ ] In folder detail, click "Remover" on an item
- [ ] Confirm removal
- [ ] Verify item removed from list

#### Test 4.7: Delete Folder
- [ ] Click "Eliminar Carpeta"
- [ ] Confirm deletion
- [ ] Verify redirect to dashboard
- [ ] Verify folder no longer appears

---

### 5. Row Level Security (RLS)

#### Test 5.1: User Isolation
**Setup**: Create two users (User A and User B)

**User A:**
- [ ] Sign up as User A
- [ ] Create project "A's Project"
- [ ] Run validation
- [ ] Create folder "A's Folder"
- [ ] Save validation to folder

**User B:**
- [ ] Sign up as User B
- [ ] Navigate to Dashboard
- [ ] **VERIFY**: Cannot see User A's validations
- [ ] Navigate to Proyectos
- [ ] **VERIFY**: Cannot see User A's projects
- [ ] Try to access User A's folder URL directly
- [ ] **VERIFY**: Returns 404 or empty (not User A's data)

---

### 6. UI Requirements

#### Test 6.1: No Emojis
- [ ] Review all pages
- [ ] **VERIFY**: No emojis appear anywhere in the UI

#### Test 6.2: Spanish Language
- [ ] Verify all UI text is in Spanish
- [ ] Verify button labels, headers, messages are Spanish

#### Test 6.3: Nueva Validacion - No "Guardar Proyecto" Button
- [ ] After running validation
- [ ] **VERIFY**: No "Guardar Proyecto" button appears
- [ ] Project is automatically saved during validation

#### Test 6.4: Catastro Disclaimer Position
- [ ] On Nueva Validacion form
- [ ] **VERIFY**: Catastro disclaimer appears ONLY under the Catastro input field
- [ ] **VERIFY**: Disclaimer does NOT appear after validation results

---

## Error Handling Tests

- [ ] Try to validate without project description: Shows error
- [ ] Try to create folder with duplicate name: Shows error
- [ ] Invalid login credentials: Shows error message
- [ ] API timeout: Shows appropriate error
- [ ] Network offline: Shows error state

---

## Performance Tests

- [ ] Dashboard loads in < 3 seconds
- [ ] Validation completes in < 60 seconds
- [ ] PDF generates in < 5 seconds
- [ ] Projects list handles 50+ projects

---

## Sign-Off

| Test Category | Pass | Fail | Notes |
|---------------|------|------|-------|
| Authentication | | | |
| Projects | | | |
| Validations | | | |
| PDF Reports | | | |
| Folders | | | |
| RLS Security | | | |
| UI Requirements | | | |

Tested by: _________________
Date: _________________
Environment: _________________
