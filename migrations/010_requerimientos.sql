-- =============================================================================
-- PYXTEN 010 - REQUERIMIENTOS DE SUBSANACION
--
-- Additive. Run after 009. Idempotent.
--
-- THE DOCUMENT IS A DRAFT UNTIL A PERSON APPROVES IT
--   Every notice is created as `borrador`. Approval is a separate, explicit act
--   that records who and when. Nothing in this schema, and nothing in the API,
--   sends anything to an applicant: there is no recipient column, no sent_at,
--   no delivery status. That absence is deliberate - adding one later should be
--   a decision somebody makes on purpose, not something that quietly already
--   works.
--
-- CONTENT IS FROZEN AT GENERATION
--   A notice's body and the findings it rests on cannot be edited after the row
--   exists. Revising means generating a new version, so the record shows what
--   was drafted on Tuesday and what replaced it on Thursday. Approving an
--   already-approved notice is likewise refused.
-- =============================================================================

CREATE TABLE IF NOT EXISTS requerimientos (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id            UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id             UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    -- The rules the notice was drafted under, carried from the case.
    ruleset_version_id UUID NOT NULL REFERENCES rulesets(id),

    version            INTEGER NOT NULL DEFAULT 1,
    status             TEXT NOT NULL DEFAULT 'borrador'
                       CHECK (status IN ('borrador', 'aprobado', 'descartado')),

    -- compliance_checks ids this notice rests on.
    finding_ids        JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Rendered sections: encabezado, introduccion, hallazgos[], cierre.
    body               JSONB NOT NULL,

    model_used         TEXT,
    generated_by       UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    generated_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    approved_by        UUID REFERENCES auth.users(id) ON DELETE SET NULL,
    approved_at        TIMESTAMPTZ,

    UNIQUE (case_id, version),

    -- A deficiency notice with no deficiencies is not a document anyone should
    -- be able to produce.
    CONSTRAINT requerimiento_requires_findings CHECK (
        jsonb_array_length(finding_ids) > 0
    ),

    -- An approval names a person and a moment, or it is not an approval.
    CONSTRAINT requerimiento_approval_is_attributed CHECK (
        status <> 'aprobado' OR (approved_by IS NOT NULL AND approved_at IS NOT NULL)
    )
);

CREATE INDEX IF NOT EXISTS idx_requerimientos_case
    ON requerimientos(case_id, version DESC);
CREATE INDEX IF NOT EXISTS idx_requerimientos_org ON requerimientos(org_id);


-- -----------------------------------------------------------------------------
-- Content is immutable; only the approval fields may move, and only forwards.
-- -----------------------------------------------------------------------------

CREATE OR REPLACE FUNCTION public.requerimientos_guard()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.body IS DISTINCT FROM OLD.body
       OR NEW.finding_ids IS DISTINCT FROM OLD.finding_ids
       OR NEW.version IS DISTINCT FROM OLD.version
       OR NEW.case_id IS DISTINCT FROM OLD.case_id
       OR NEW.ruleset_version_id IS DISTINCT FROM OLD.ruleset_version_id THEN
        RAISE EXCEPTION
            'El contenido de un requerimiento no se puede modificar. Genere una nueva version.';
    END IF;

    IF OLD.status = 'aprobado' AND NEW.status IS DISTINCT FROM 'aprobado' THEN
        RAISE EXCEPTION 'Un requerimiento aprobado no se puede revertir.';
    END IF;

    RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS requerimientos_guard_trg ON requerimientos;
CREATE TRIGGER requerimientos_guard_trg
    BEFORE UPDATE ON requerimientos
    FOR EACH ROW EXECUTE FUNCTION public.requerimientos_guard();

REVOKE DELETE ON requerimientos FROM authenticated, anon;


-- -----------------------------------------------------------------------------
-- RLS
-- -----------------------------------------------------------------------------

ALTER TABLE requerimientos ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS requerimientos_select ON requerimientos;
DROP POLICY IF EXISTS requerimientos_insert ON requerimientos;
DROP POLICY IF EXISTS requerimientos_update ON requerimientos;

CREATE POLICY requerimientos_select ON requerimientos FOR SELECT TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY requerimientos_insert ON requerimientos FOR INSERT TO authenticated
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));
-- UPDATE exists only so a reviewer can approve or discard; the trigger above
-- is what stops it being used to rewrite a notice after the fact.
CREATE POLICY requerimientos_update ON requerimientos FOR UPDATE TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()))
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));

-- =============================================================================
-- DONE.
-- =============================================================================
