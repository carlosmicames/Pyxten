-- =============================================================================
-- PYXTEN 005 - REVIEWER CONSOLE, PHASE 1 (case model + intake)
--
-- Additive only. This file creates new tables and a new storage bucket. It does
-- not alter, drop, or re-policy anything the applicant product uses.
--
-- Run in the Supabase SQL Editor. Idempotent - safe to re-run.
--
-- TENANCY MODEL
-- Every reviewer table carries org_id. The API reaches these tables as the
-- signed-in user (PostgREST + the caller's JWT), so the policies below are what
-- actually enforces "a reviewer in Municipality A can never read a case from
-- Municipality B" - they are not decoration on top of a superuser connection.
--
-- GUARDRAILS THAT LIVE IN THE SCHEMA (not just in application code)
--   * extracted_facts: a fact may only claim status 'extraido' if it points at a
--     specific document AND page. Otherwise it must say so explicitly.
--   * audit_events: append-only, enforced by trigger and by REVOKE.
--   * cases.ruleset_version_id: immutable once the case exists.
--   * rulesets: a published ruleset can never be edited.
-- =============================================================================


-- =============================================================================
-- 1. RULESETS - versioned regulation snapshots
--
-- Phase 2 fills `content` with the rules currently living as Python constants in
-- api/app/services/*.py. Phase 1 only needs the version to exist so every case
-- can be permanently stamped with the rules in force when it was opened.
-- =============================================================================

CREATE TABLE IF NOT EXISTS rulesets (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    permit_type   TEXT NOT NULL DEFAULT 'permiso_unico',
    version       TEXT NOT NULL,
    name          TEXT NOT NULL,
    content       JSONB NOT NULL DEFAULT '{}'::jsonb,
    published_at  TIMESTAMPTZ,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (permit_type, version)
);

-- A published ruleset is frozen. Historical cases point at it and must keep
-- resolving to exactly the rules that were in force.
CREATE OR REPLACE FUNCTION public.rulesets_block_published_edit()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF OLD.published_at IS NOT NULL
       AND (NEW.content IS DISTINCT FROM OLD.content
            OR NEW.version IS DISTINCT FROM OLD.version
            OR NEW.permit_type IS DISTINCT FROM OLD.permit_type) THEN
        RAISE EXCEPTION
            'ruleset % is published and cannot be modified; publish a new version instead',
            OLD.version;
    END IF;
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS rulesets_no_edit_after_publish ON rulesets;
CREATE TRIGGER rulesets_no_edit_after_publish
    BEFORE UPDATE ON rulesets
    FOR EACH ROW EXECUTE FUNCTION public.rulesets_block_published_edit();


-- =============================================================================
-- 2. ORGANIZATIONS AND MEMBERSHIP
-- =============================================================================

CREATE TABLE IF NOT EXISTS organizations (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name              TEXT NOT NULL,
    municipality      TEXT NOT NULL,
    active_ruleset_id UUID REFERENCES rulesets(id),
    config            JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS org_members (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id     UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    user_id    UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    role       TEXT NOT NULL CHECK (role IN ('intake', 'reviewer', 'supervisor', 'auditor')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (org_id, user_id)
);

CREATE INDEX IF NOT EXISTS idx_org_members_user ON org_members(user_id);
CREATE INDEX IF NOT EXISTS idx_org_members_org  ON org_members(org_id);


-- -----------------------------------------------------------------------------
-- The tenancy helper.
--
-- SECURITY DEFINER matters here: every policy below asks "is this row's org one
-- of mine?", and if that question were answered by a plain subquery against
-- org_members, that subquery would itself be filtered by org_members' own
-- policy - recursion. A definer-rights function answers it once, cleanly.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.reviewer_org_ids()
RETURNS SETOF UUID
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT org_id FROM public.org_members WHERE user_id = auth.uid();
$$;

-- Role lookup, for routes that need more than membership (e.g. only a
-- supervisor may reassign a case). Returns NULL when not a member.
CREATE OR REPLACE FUNCTION public.reviewer_role_in(target_org UUID)
RETURNS TEXT
LANGUAGE sql
SECURITY DEFINER
STABLE
SET search_path = public
AS $$
    SELECT role FROM public.org_members
    WHERE user_id = auth.uid() AND org_id = target_org
    LIMIT 1;
$$;


-- =============================================================================
-- 3. CASES
-- =============================================================================

CREATE TABLE IF NOT EXISTS cases (
    id                   UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id               UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    case_number          TEXT NOT NULL,
    permit_type          TEXT NOT NULL DEFAULT 'permiso_unico',
    applicant_name       TEXT,
    property_address     TEXT,
    catastro             TEXT,
    status               TEXT NOT NULL DEFAULT 'recibido'
                         CHECK (status IN ('recibido', 'en_revision', 'borrador_requerimiento', 'cerrado')),
    assigned_reviewer_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    ruleset_version_id   UUID NOT NULL REFERENCES rulesets(id),
    created_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (org_id, case_number)
);

CREATE INDEX IF NOT EXISTS idx_cases_org_status  ON cases(org_id, status);
CREATE INDEX IF NOT EXISTS idx_cases_assignee    ON cases(assigned_reviewer_id);
CREATE INDEX IF NOT EXISTS idx_cases_created_at  ON cases(created_at DESC);

-- The ruleset stamp is the whole point of versioning: it cannot drift after the
-- fact, or a determination stops being reproducible.
CREATE OR REPLACE FUNCTION public.cases_freeze_ruleset()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.ruleset_version_id IS DISTINCT FROM OLD.ruleset_version_id THEN
        RAISE EXCEPTION
            'cases.ruleset_version_id is immutable (case %); open a new case to evaluate under a different ruleset',
            OLD.id;
    END IF;
    NEW.updated_at := NOW();
    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS cases_freeze_ruleset_trg ON cases;
CREATE TRIGGER cases_freeze_ruleset_trg
    BEFORE UPDATE ON cases
    FOR EACH ROW EXECUTE FUNCTION public.cases_freeze_ruleset();


-- =============================================================================
-- 4. CASE DOCUMENTS
-- =============================================================================

CREATE TABLE IF NOT EXISTS case_documents (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id             UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id              UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    filename            TEXT NOT NULL,

    -- 'desconocido' is a legitimate outcome, not a failure. Never force a guess.
    doc_type            TEXT NOT NULL DEFAULT 'desconocido',
    -- Who decided the type: nobody yet, the model, or a human reviewer.
    doc_type_source     TEXT NOT NULL DEFAULT 'pendiente'
                        CHECK (doc_type_source IN ('pendiente', 'modelo', 'revisor')),
    -- Categorical band only. There is deliberately no numeric confidence column:
    -- a percentage in this table would eventually end up in an appeal record.
    classification_band TEXT CHECK (classification_band IN ('alta', 'media', 'baja')),
    -- Machine-generated explanation of how the band was reached.
    classification_reason TEXT,
    -- Page the classification was read from, so even a doc_type is evidence-linked.
    classification_page INTEGER,

    storage_uri         TEXT NOT NULL,
    sha256              TEXT NOT NULL,
    page_count          INTEGER,
    text_char_count     INTEGER,

    ocr_status          TEXT NOT NULL DEFAULT 'pendiente'
                        CHECK (ocr_status IN ('pendiente', 'texto_incrustado', 'sin_texto', 'parcial', 'error')),
    processing_status   TEXT NOT NULL DEFAULT 'recibido'
                        CHECK (processing_status IN ('recibido', 'extrayendo', 'clasificando', 'listo', 'error')),
    processing_error    TEXT,

    uploaded_at         TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- The same file uploaded twice into one case is one document.
    UNIQUE (case_id, sha256)
);

CREATE INDEX IF NOT EXISTS idx_case_documents_case ON case_documents(case_id);
CREATE INDEX IF NOT EXISTS idx_case_documents_org  ON case_documents(org_id);


-- =============================================================================
-- 5. DOCUMENT PAGES
--
-- Page-level text is what makes "document + page" citations addressable. Storing
-- one blob per document would turn every citation into a scan.
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_pages (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id       UUID NOT NULL REFERENCES case_documents(id) ON DELETE CASCADE,
    org_id            UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    page_no           INTEGER NOT NULL CHECK (page_no >= 1),
    text              TEXT,
    char_count        INTEGER NOT NULL DEFAULT 0,
    extraction_method TEXT NOT NULL DEFAULT 'pdf_text'
                      CHECK (extraction_method IN ('pdf_text', 'ocr', 'ninguno')),
    UNIQUE (document_id, page_no)
);

CREATE INDEX IF NOT EXISTS idx_document_pages_doc ON document_pages(document_id);


-- =============================================================================
-- 6. EXTRACTED FACTS
--
-- Created in Phase 1, populated in Phase 2. The evidence constraint is here from
-- the start so no code path can ever write a fact without provenance.
-- =============================================================================

CREATE TABLE IF NOT EXISTS extracted_facts (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id      UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    document_id  UUID REFERENCES case_documents(id) ON DELETE CASCADE,
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    field_key    TEXT NOT NULL,
    value_text   TEXT,
    value_date   DATE,
    value_num    NUMERIC,
    source_page  INTEGER,
    source_bbox  JSONB,
    band         TEXT NOT NULL CHECK (band IN ('alta', 'media', 'baja')),
    status       TEXT NOT NULL DEFAULT 'extraido'
                 CHECK (status IN ('extraido', 'evidencia_no_disponible', 'contradictorio')),
    extracted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- No finding without evidence. A fact asserted as extracted must name the
    -- document and the page it came from; anything else has to declare itself
    -- as evidence-unavailable or contradictory.
    CONSTRAINT extracted_facts_evidence_required CHECK (
        status <> 'extraido'
        OR (document_id IS NOT NULL AND source_page IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_extracted_facts_case ON extracted_facts(case_id);


-- =============================================================================
-- 7. AUDIT EVENTS - append only
-- =============================================================================

CREATE TABLE IF NOT EXISTS audit_events (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    org_id        UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    case_id       UUID REFERENCES cases(id) ON DELETE CASCADE,
    actor_user_id UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    event_type    TEXT NOT NULL,
    object_ref    TEXT,
    payload       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_events_case    ON audit_events(case_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_audit_events_org     ON audit_events(org_id, created_at DESC);

CREATE OR REPLACE FUNCTION public.audit_events_append_only()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_events is append-only; % is not permitted', TG_OP;
END;
$$;

DROP TRIGGER IF EXISTS audit_events_no_update ON audit_events;
CREATE TRIGGER audit_events_no_update
    BEFORE UPDATE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION public.audit_events_append_only();

DROP TRIGGER IF EXISTS audit_events_no_delete ON audit_events;
CREATE TRIGGER audit_events_no_delete
    BEFORE DELETE ON audit_events
    FOR EACH ROW EXECUTE FUNCTION public.audit_events_append_only();

-- Belt and braces: no UPDATE/DELETE grant at all for API roles, so a future
-- permissive policy cannot quietly re-open the door.
REVOKE UPDATE, DELETE ON audit_events FROM authenticated, anon;


-- =============================================================================
-- 8. ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE rulesets        ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations   ENABLE ROW LEVEL SECURITY;
ALTER TABLE org_members     ENABLE ROW LEVEL SECURITY;
ALTER TABLE cases           ENABLE ROW LEVEL SECURITY;
ALTER TABLE case_documents  ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_pages  ENABLE ROW LEVEL SECURITY;
ALTER TABLE extracted_facts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_events    ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS rulesets_read              ON rulesets;
DROP POLICY IF EXISTS organizations_read         ON organizations;
DROP POLICY IF EXISTS org_members_read           ON org_members;
DROP POLICY IF EXISTS cases_select               ON cases;
DROP POLICY IF EXISTS cases_insert               ON cases;
DROP POLICY IF EXISTS cases_update               ON cases;
DROP POLICY IF EXISTS case_documents_select      ON case_documents;
DROP POLICY IF EXISTS case_documents_insert      ON case_documents;
DROP POLICY IF EXISTS case_documents_update      ON case_documents;
DROP POLICY IF EXISTS document_pages_select      ON document_pages;
DROP POLICY IF EXISTS document_pages_insert      ON document_pages;
DROP POLICY IF EXISTS extracted_facts_select     ON extracted_facts;
DROP POLICY IF EXISTS extracted_facts_insert     ON extracted_facts;
DROP POLICY IF EXISTS audit_events_select        ON audit_events;
DROP POLICY IF EXISTS audit_events_insert        ON audit_events;

-- Rulesets are shared reference data, readable by any authenticated member.
-- They are never written through the API in Phase 1.
CREATE POLICY rulesets_read ON rulesets FOR SELECT TO authenticated USING (TRUE);

CREATE POLICY organizations_read ON organizations FOR SELECT TO authenticated
    USING (id IN (SELECT public.reviewer_org_ids()));

CREATE POLICY org_members_read ON org_members FOR SELECT TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()));

CREATE POLICY cases_select ON cases FOR SELECT TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY cases_insert ON cases FOR INSERT TO authenticated
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY cases_update ON cases FOR UPDATE TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()))
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));

CREATE POLICY case_documents_select ON case_documents FOR SELECT TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY case_documents_insert ON case_documents FOR INSERT TO authenticated
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY case_documents_update ON case_documents FOR UPDATE TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()))
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));

CREATE POLICY document_pages_select ON document_pages FOR SELECT TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY document_pages_insert ON document_pages FOR INSERT TO authenticated
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));

CREATE POLICY extracted_facts_select ON extracted_facts FOR SELECT TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY extracted_facts_insert ON extracted_facts FOR INSERT TO authenticated
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));

CREATE POLICY audit_events_select ON audit_events FOR SELECT TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY audit_events_insert ON audit_events FOR INSERT TO authenticated
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));
-- Deliberately no UPDATE or DELETE policy on audit_events.


-- =============================================================================
-- 9. STORAGE - the `expedientes` bucket
--
-- Private. Path shape is  {org_id}/{case_id}/{document_id}.pdf  so the very first
-- segment is the tenant boundary, and the policy can enforce it directly.
-- =============================================================================

INSERT INTO storage.buckets (id, name, public)
VALUES ('expedientes', 'expedientes', false)
ON CONFLICT (id) DO UPDATE SET public = false;

CREATE OR REPLACE FUNCTION public.expediente_path_is_mine(object_name TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, storage
AS $$
DECLARE
    segments TEXT[];
    candidate UUID;
BEGIN
    segments := storage.foldername(object_name);

    IF array_length(segments, 1) IS NULL OR array_length(segments, 1) < 1 THEN
        RETURN FALSE;
    END IF;

    BEGIN
        candidate := segments[1]::uuid;
    EXCEPTION WHEN others THEN
        RETURN FALSE;
    END;

    RETURN EXISTS (
        SELECT 1 FROM public.org_members
        WHERE user_id = auth.uid() AND org_id = candidate
    );
END;
$$;

DROP POLICY IF EXISTS expedientes_insert ON storage.objects;
DROP POLICY IF EXISTS expedientes_select ON storage.objects;
DROP POLICY IF EXISTS expedientes_delete ON storage.objects;

CREATE POLICY expedientes_insert ON storage.objects FOR INSERT TO authenticated
    WITH CHECK (bucket_id = 'expedientes' AND public.expediente_path_is_mine(name));

CREATE POLICY expedientes_select ON storage.objects FOR SELECT TO authenticated
    USING (bucket_id = 'expedientes' AND public.expediente_path_is_mine(name));

CREATE POLICY expedientes_delete ON storage.objects FOR DELETE TO authenticated
    USING (bucket_id = 'expedientes' AND public.expediente_path_is_mine(name));


-- =============================================================================
-- 10. SEED - baseline ruleset and the San Juan pilot organization
-- =============================================================================

INSERT INTO rulesets (permit_type, version, name, content, published_at)
VALUES (
    'permiso_unico',
    'pu-2026.0',
    'Permiso Unico - linea base (taxonomia de documentos)',
    jsonb_build_object(
        'note', 'Phase 1 baseline. Document taxonomy only; rule bodies are migrated out of Python constants in Phase 2.',
        'source', 'api/app/services/document_service.py PERMISO_UNICO_DOCUMENTS'
    ),
    NOW()
)
ON CONFLICT (permit_type, version) DO NOTHING;

INSERT INTO organizations (name, municipality, active_ruleset_id, config)
SELECT
    'Municipio de San Juan',
    'San Juan',
    r.id,
    jsonb_build_object(
        'case_number_prefix', 'SJ',
        'usa_codigos_pot_municipales', TRUE
    )
FROM rulesets r
WHERE r.permit_type = 'permiso_unico' AND r.version = 'pu-2026.0'
  AND NOT EXISTS (SELECT 1 FROM organizations o WHERE o.municipality = 'San Juan')
LIMIT 1;


-- =============================================================================
-- 11. BOOTSTRAP HELPER - grant a person access to an organization
--
-- Run this once per reviewer, from the SQL Editor:
--
--     SELECT public.reviewer_grant('persona@sanjuan.pr.gov', 'San Juan', 'reviewer');
--
-- Roles: intake | reviewer | supervisor | auditor
-- The person must already have signed up (so an auth.users row exists).
-- =============================================================================

CREATE OR REPLACE FUNCTION public.reviewer_grant(
    member_email      TEXT,
    org_municipality  TEXT,
    member_role       TEXT DEFAULT 'reviewer'
)
RETURNS TEXT
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
DECLARE
    target_user UUID;
    target_org  UUID;
BEGIN
    SELECT id INTO target_user FROM auth.users WHERE lower(email) = lower(member_email);
    IF target_user IS NULL THEN
        RETURN format('No existe un usuario con el correo %s. Debe registrarse primero.', member_email);
    END IF;

    SELECT id INTO target_org FROM organizations WHERE municipality = org_municipality;
    IF target_org IS NULL THEN
        RETURN format('No existe una organizacion para el municipio %s.', org_municipality);
    END IF;

    INSERT INTO org_members (org_id, user_id, role)
    VALUES (target_org, target_user, member_role)
    ON CONFLICT (org_id, user_id) DO UPDATE SET role = EXCLUDED.role;

    RETURN format('%s ahora tiene el rol %s en %s.', member_email, member_role, org_municipality);
END;
$$;

-- =============================================================================
-- DONE.
-- =============================================================================
