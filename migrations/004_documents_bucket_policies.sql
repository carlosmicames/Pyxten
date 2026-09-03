-- =============================================================================
-- PYXTEN 004 - STORAGE POLICIES FOR THE PRIVATE `documents` BUCKET
--
-- WHY THIS EXISTS
-- The `documents` bucket was switched from public to private. That closed a real
-- exposure (anyone with a URL could read escrituras, planos, certificaciones de
-- Hacienda/ASUME), but a private bucket denies ALL access until explicit Row
-- Level Security policies exist on storage.objects. Without the policies below:
--   - uploads from /validacion-documentos fail, and
--   - every previously stored link 400s.
--
-- Run this in the Supabase SQL Editor. It is idempotent.
--
-- NOTE ON PATHS
-- The uploader (frontend/lib/storage.ts) writes to:
--     validations/{document_validation_id}/{docCode}_{timestamp}_{filename}.pdf
-- so storage.foldername(name) evaluates to:
--     [1] = 'validations'
--     [2] = the document_validations.id
-- Ownership is therefore proved by joining segment [2] back to document_validations.
-- (An earlier draft in migration 003's comments compared segment [1] to auth.uid();
-- that would have rejected every upload this app actually makes.)
-- =============================================================================

-- -----------------------------------------------------------------------------
-- 1. Make sure the bucket exists and is private.
--    If you already flipped it to private in the dashboard this is a no-op.
-- -----------------------------------------------------------------------------

INSERT INTO storage.buckets (id, name, public)
VALUES ('documents', 'documents', false)
ON CONFLICT (id) DO UPDATE SET public = false;

-- -----------------------------------------------------------------------------
-- 2. Drop old policies so this file can be re-run safely.
-- -----------------------------------------------------------------------------

DROP POLICY IF EXISTS "Users can upload own documents"        ON storage.objects;
DROP POLICY IF EXISTS "Users can view own documents"          ON storage.objects;
DROP POLICY IF EXISTS "Users can delete own documents"        ON storage.objects;
DROP POLICY IF EXISTS "documents_insert_own_validation"       ON storage.objects;
DROP POLICY IF EXISTS "documents_select_own_validation"       ON storage.objects;
DROP POLICY IF EXISTS "documents_update_own_validation"       ON storage.objects;
DROP POLICY IF EXISTS "documents_delete_own_validation"       ON storage.objects;

-- -----------------------------------------------------------------------------
-- 3. Helper: does the signed-in user own the document_validations row named by
--    the second path segment?
--
--    SECURITY DEFINER so the check itself is not subject to RLS recursion.
--    STABLE so Postgres can cache it within a statement.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.owns_document_validation_path(object_name TEXT)
RETURNS BOOLEAN
LANGUAGE plpgsql
SECURITY DEFINER
STABLE
SET search_path = public, storage
AS $$
DECLARE
    segments TEXT[];
    validation_uuid UUID;
BEGIN
    segments := storage.foldername(object_name);

    -- Expect exactly the shape validations/{uuid}/...
    IF array_length(segments, 1) IS NULL OR array_length(segments, 1) < 2 THEN
        RETURN FALSE;
    END IF;

    IF segments[1] <> 'validations' THEN
        RETURN FALSE;
    END IF;

    -- A malformed segment must deny, not raise.
    BEGIN
        validation_uuid := segments[2]::uuid;
    EXCEPTION WHEN others THEN
        RETURN FALSE;
    END;

    RETURN EXISTS (
        SELECT 1
        FROM public.document_validations dv
        WHERE dv.id = validation_uuid
          AND dv.user_id = auth.uid()
    );
END;
$$;

-- -----------------------------------------------------------------------------
-- 4. Policies. Authenticated users only; anonymous access is never granted.
-- -----------------------------------------------------------------------------

CREATE POLICY "documents_insert_own_validation"
ON storage.objects FOR INSERT TO authenticated
WITH CHECK (
    bucket_id = 'documents'
    AND public.owns_document_validation_path(name)
);

CREATE POLICY "documents_select_own_validation"
ON storage.objects FOR SELECT TO authenticated
USING (
    bucket_id = 'documents'
    AND public.owns_document_validation_path(name)
);

CREATE POLICY "documents_update_own_validation"
ON storage.objects FOR UPDATE TO authenticated
USING (
    bucket_id = 'documents'
    AND public.owns_document_validation_path(name)
)
WITH CHECK (
    bucket_id = 'documents'
    AND public.owns_document_validation_path(name)
);

CREATE POLICY "documents_delete_own_validation"
ON storage.objects FOR DELETE TO authenticated
USING (
    bucket_id = 'documents'
    AND public.owns_document_validation_path(name)
);

-- =============================================================================
-- AFTER RUNNING THIS
-- Deploy the matching frontend change (frontend/lib/storage.ts). Stored links
-- are now generated on demand as short-lived signed URLs; the public URLs
-- written before the bucket was made private are read back by extracting their
-- path and re-signing it, so old rows keep working without a data migration.
-- =============================================================================
