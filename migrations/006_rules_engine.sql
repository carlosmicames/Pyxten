-- =============================================================================
-- PYXTEN 006 - RULE ENGINE (Phase 2, part 1: storage)
--
-- Additive only. Extends `rulesets` from migration 005 and adds the four tables
-- the deterministic evaluator reads and writes.
--
-- Run in the Supabase SQL Editor after 005. Idempotent.
--
-- SHARED BASELINE, PER-ORG OVERRIDE
--   A ruleset with org_id IS NULL is the shared baseline every municipality
--   inherits. A municipality that needs to diverge publishes its own ruleset
--   with org_id set and parent_ruleset_id pointing at the baseline it derives
--   from. A case is stamped with whichever ruleset its office had active.
--
-- WHY compliance_checks IS APPEND-ONLY
--   Re-evaluating a case after a document is replaced must not erase what the
--   system concluded before. Rows accumulate; `compliance_checks_current` is the
--   view that answers "what does this case look like now".
-- =============================================================================


-- =============================================================================
-- 1. RULESETS - versioning, approval, effectivity
-- =============================================================================

ALTER TABLE rulesets ADD COLUMN IF NOT EXISTS org_id UUID REFERENCES organizations(id) ON DELETE CASCADE;
ALTER TABLE rulesets ADD COLUMN IF NOT EXISTS parent_ruleset_id UUID REFERENCES rulesets(id);
ALTER TABLE rulesets ADD COLUMN IF NOT EXISTS effective_from DATE;
ALTER TABLE rulesets ADD COLUMN IF NOT EXISTS effective_to DATE;
ALTER TABLE rulesets ADD COLUMN IF NOT EXISTS approved_by UUID REFERENCES auth.users(id);
ALTER TABLE rulesets ADD COLUMN IF NOT EXISTS approved_at TIMESTAMPTZ;
ALTER TABLE rulesets ADD COLUMN IF NOT EXISTS status TEXT NOT NULL DEFAULT 'borrador';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'rulesets_status_check'
    ) THEN
        ALTER TABLE rulesets ADD CONSTRAINT rulesets_status_check
            CHECK (status IN ('borrador', 'publicado', 'archivado'));
    END IF;
END $$;

-- The row seeded by 005 is already in force; make that explicit.
UPDATE rulesets
   SET status = 'publicado',
       effective_from = COALESCE(effective_from, created_at::date)
 WHERE published_at IS NOT NULL AND status = 'borrador';

CREATE INDEX IF NOT EXISTS idx_rulesets_org ON rulesets(org_id, permit_type, status);


-- =============================================================================
-- 2. DOCUMENT TYPES - the taxonomy, as configuration
--
-- Versioned with the ruleset, because a checklist change IS a rules change: a
-- case decided under last year's checklist has to keep resolving to it.
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_types (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruleset_id  UUID NOT NULL REFERENCES rulesets(id) ON DELETE CASCADE,
    code        TEXT NOT NULL,
    name        TEXT NOT NULL,
    description TEXT,
    sort_order  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (ruleset_id, code)
);

CREATE INDEX IF NOT EXISTS idx_document_types_ruleset ON document_types(ruleset_id);


-- =============================================================================
-- 3. RULES
-- =============================================================================

CREATE TABLE IF NOT EXISTS rules (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruleset_id        UUID NOT NULL REFERENCES rulesets(id) ON DELETE CASCADE,
    code              TEXT NOT NULL,
    title             TEXT NOT NULL,
    family            TEXT NOT NULL
                      CHECK (family IN ('presencia', 'vigencia', 'consistencia', 'aplicabilidad')),
    -- Which instrument the rule rests on.
    authority         TEXT,
    -- The quotable reference that can appear in a signed notice.
    citation          TEXT,
    applies_when      JSONB,
    required_evidence JSONB NOT NULL DEFAULT '[]'::jsonb,
    pass_condition    JSONB,
    fail_condition    JSONB,
    review_condition  JSONB,
    severity          TEXT NOT NULL DEFAULT 'moderada'
                      CHECK (severity IN ('leve', 'moderada', 'grave')),
    enabled           BOOLEAN NOT NULL DEFAULT TRUE,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (ruleset_id, code),

    -- A rule with no legal citation may escalate to a reviewer, but it must not
    -- be able to accuse: an uncited finding cannot be defended in a notice.
    -- (The evaluator enforces the same rule; this stops it being authored at all.)
    CONSTRAINT rules_finding_requires_citation CHECK (
        fail_condition IS NULL OR citation IS NOT NULL
    )
);

CREATE INDEX IF NOT EXISTS idx_rules_ruleset ON rules(ruleset_id, enabled);


-- =============================================================================
-- 4. COMPLIANCE CHECKS - append-only
-- =============================================================================

CREATE TABLE IF NOT EXISTS compliance_checks (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id      UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    rule_id      UUID NOT NULL REFERENCES rules(id),
    -- Denormalized so the consistency constraint below can be expressed at all.
    family       TEXT NOT NULL,

    status       TEXT NOT NULL
                 CHECK (status IN ('sin_hallazgos', 'hallazgo_identificado', 'requiere_criterio')),
    band         TEXT NOT NULL CHECK (band IN ('alta', 'media', 'baja')),

    -- case_documents ids backing this conclusion.
    evidence_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    -- Per-field provenance: field, document, page, value, band.
    citations    JSONB NOT NULL DEFAULT '[]'::jsonb,

    explanation  TEXT NOT NULL,
    reason_code  TEXT,
    evaluated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- No finding without evidence.
    CONSTRAINT checks_finding_requires_evidence CHECK (
        status <> 'hallazgo_identificado' OR jsonb_array_length(evidence_ids) > 0
    ),

    -- A contradiction claim has two sides, and the notice must cite both.
    CONSTRAINT checks_inconsistency_cites_two CHECK (
        status <> 'hallazgo_identificado'
        OR family <> 'consistencia'
        OR jsonb_array_length(evidence_ids) >= 2
    ),

    -- Every escalation names its trigger.
    CONSTRAINT checks_review_requires_reason CHECK (
        status <> 'requiere_criterio' OR reason_code IS NOT NULL
    ),

    -- A low band always escalates; nothing may conclude on weak evidence.
    CONSTRAINT checks_low_band_escalates CHECK (
        band <> 'baja' OR status = 'requiere_criterio'
    )
);

CREATE INDEX IF NOT EXISTS idx_checks_case ON compliance_checks(case_id, evaluated_at DESC);
CREATE INDEX IF NOT EXISTS idx_checks_org  ON compliance_checks(org_id);

CREATE OR REPLACE FUNCTION public.compliance_checks_append_only()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'compliance_checks is append-only; % is not permitted. Re-evaluate to add a new row.', TG_OP;
END;
$$;

DROP TRIGGER IF EXISTS compliance_checks_no_update ON compliance_checks;
CREATE TRIGGER compliance_checks_no_update
    BEFORE UPDATE ON compliance_checks
    FOR EACH ROW EXECUTE FUNCTION public.compliance_checks_append_only();

DROP TRIGGER IF EXISTS compliance_checks_no_delete ON compliance_checks;
CREATE TRIGGER compliance_checks_no_delete
    BEFORE DELETE ON compliance_checks
    FOR EACH ROW EXECUTE FUNCTION public.compliance_checks_append_only();

REVOKE UPDATE, DELETE ON compliance_checks FROM authenticated, anon;

-- The latest evaluation of each rule per case.
CREATE OR REPLACE VIEW compliance_checks_current AS
SELECT DISTINCT ON (case_id, rule_id) *
  FROM compliance_checks
 ORDER BY case_id, rule_id, evaluated_at DESC;


-- =============================================================================
-- 5. EXTERNAL VERIFICATIONS
--
-- GIS is evidence, not truth. Every lookup is recorded with its raw response so
-- a determination stays reproducible after the commonwealth changes a field
-- name, and so a reviewer can see exactly what the service said.
-- =============================================================================

CREATE TABLE IF NOT EXISTS external_verifications (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    case_id      UUID NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
    org_id       UUID NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
    source       TEXT NOT NULL,
    query        JSONB NOT NULL DEFAULT '{}'::jsonb,
    response     JSONB NOT NULL DEFAULT '{}'::jsonb,
    matched      BOOLEAN,
    quality_flag TEXT NOT NULL DEFAULT 'ok'
                 CHECK (quality_flag IN (
                     'ok',                  -- clean single result
                     'sin_resultado',       -- service answered, nothing there
                     'ambiguo',             -- more than one parcel matched
                     'fuera_de_servicio',   -- timeout or error
                     'esquema_inesperado'   -- fields absent from the response
                 )),
    retrieved_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_external_case ON external_verifications(case_id, retrieved_at DESC);


-- =============================================================================
-- 6. ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE document_types          ENABLE ROW LEVEL SECURITY;
ALTER TABLE rules                   ENABLE ROW LEVEL SECURITY;
ALTER TABLE compliance_checks       ENABLE ROW LEVEL SECURITY;
ALTER TABLE external_verifications  ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS document_types_read     ON document_types;
DROP POLICY IF EXISTS rules_read              ON rules;
DROP POLICY IF EXISTS checks_select           ON compliance_checks;
DROP POLICY IF EXISTS checks_insert           ON compliance_checks;
DROP POLICY IF EXISTS external_select         ON external_verifications;
DROP POLICY IF EXISTS external_insert         ON external_verifications;

-- Taxonomy and rules are reference data: readable by any authenticated member,
-- and never written through the API. Publishing a ruleset is a SQL operation.
CREATE POLICY document_types_read ON document_types FOR SELECT TO authenticated USING (TRUE);
CREATE POLICY rules_read          ON rules          FOR SELECT TO authenticated USING (TRUE);

CREATE POLICY checks_select ON compliance_checks FOR SELECT TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY checks_insert ON compliance_checks FOR INSERT TO authenticated
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));
-- Deliberately no UPDATE or DELETE policy.

CREATE POLICY external_select ON external_verifications FOR SELECT TO authenticated
    USING (org_id IN (SELECT public.reviewer_org_ids()));
CREATE POLICY external_insert ON external_verifications FOR INSERT TO authenticated
    WITH CHECK (org_id IN (SELECT public.reviewer_org_ids()));


-- =============================================================================
-- 7. BASELINE RULESET
--
-- Shared baseline (org_id IS NULL). Rule bodies arrive in migration 007.
-- =============================================================================

INSERT INTO rulesets (
    org_id, permit_type, version, name, content, status, effective_from, published_at
)
VALUES (
    NULL,
    'permiso_unico',
    'pu-2026.1',
    'Permiso Unico - linea base compartida',
    jsonb_build_object(
        'note', 'Shared baseline. Municipalities that diverge publish a child ruleset with parent_ruleset_id set to this row.'
    ),
    'publicado',
    CURRENT_DATE,
    NOW()
)
ON CONFLICT (permit_type, version) DO NOTHING;


-- =============================================================================
-- 8. TAXONOMY SEED - keyed by permit type, both lists kept
--
-- The business Permiso Unico checklist. CONFIRM AGAINST SAN JUAN'S ACTUAL
-- CHECKLIST before relying on it; codes are normalised entity-last throughout.
-- =============================================================================

INSERT INTO document_types (ruleset_id, code, name, description, sort_order)
SELECT r.id, d.code, d.name, d.description, d.sort_order
  FROM rulesets r
  CROSS JOIN (VALUES
    ('registro_comerciante',   'Registro de Comerciante',            'Registro de comerciante del Departamento de Hacienda', 10),
    ('patente_municipal',      'Patente Municipal',                  'Licencia municipal de negocio (patente)', 20),
    ('certificacion_crim',     'Certificacion CRIM',                 'Certificacion del Centro de Recaudacion de Ingresos Municipales', 30),
    ('certificacion_asume',    'Certificacion ASUME',                'Certificacion de cumplimiento de pension alimentaria', 40),
    ('certificado_bomberos',   'Certificado de Bomberos',            'Certificado del Negociado del Cuerpo de Bomberos de Puerto Rico', 50),
    ('certificado_salud',      'Certificado de Salud',               'Certificado del Departamento de Salud', 60),
    ('certificacion_ada',      'Certificacion ADA',                  'Certificacion de accesibilidad conforme al ADA', 70),
    ('contrato_arrendamiento', 'Contrato de Arrendamiento',          'Contrato de arrendamiento del local', 80),
    ('escritura_titularidad',  'Escritura de Titularidad',           'Escritura que acredita titularidad del inmueble', 90),
    ('plano_distribucion',     'Plano de Distribucion',              'Plano de distribucion interior del local', 100),
    ('poder_representacion',   'Poder de Representacion',            'Poder notarial cuando quien radica no es el solicitante', 110),
    ('desconocido',            'Desconocido',                        'No corresponde claramente a ninguna categoria, o no hay evidencia suficiente', 999)
  ) AS d(code, name, description, sort_order)
 WHERE r.permit_type = 'permiso_unico' AND r.version = 'pu-2026.1'
ON CONFLICT (ruleset_id, code) DO NOTHING;


-- -----------------------------------------------------------------------------
-- The second list, kept rather than discarded.
--
-- These nine document types are what api/app/services/document_service.py has
-- been serving under the name PERMISO_UNICO_DOCUMENTS. They are not a business
-- permit checklist - they are the standing-and-clearance document set that
-- accompanies a land or construction filing, and the name was wrong.
--
-- Keyed here as `documentos_generales`. If San Juan calls this set something
-- else, renaming it is one UPDATE against rulesets.permit_type; the applicant
-- product is unaffected either way, because it still reads the Python constant.
-- -----------------------------------------------------------------------------

INSERT INTO rulesets (org_id, permit_type, version, name, content, status, effective_from, published_at)
VALUES (
    NULL,
    'documentos_generales',
    'dg-2026.1',
    'Documentos generales de radicacion - linea base compartida',
    jsonb_build_object(
        'note', 'Formerly mislabelled PERMISO_UNICO_DOCUMENTS in document_service.py. Permit type name pending confirmation.'
    ),
    'publicado',
    CURRENT_DATE,
    NOW()
)
ON CONFLICT (permit_type, version) DO NOTHING;

INSERT INTO document_types (ruleset_id, code, name, description, sort_order)
SELECT r.id, d.code, d.name, d.description, d.sort_order
  FROM rulesets r
  CROSS JOIN (VALUES
    ('legitimacion_activa',      'Legitimacion Activa',              'Documento que acredita el derecho del solicitante sobre la propiedad', 10),
    ('identificacion',           'Identificacion del Solicitante',   'Copia de identificacion con foto', 20),
    ('estatus_corporativo',      'Estatus Corporativo',              'Certificado de existencia corporativa del Departamento de Estado', 30),
    ('poder_representacion',     'Poder de Representacion',          'Poder notarial si el solicitante actua en representacion de otro', 40),
    ('escritura_propiedad',      'Escritura de Propiedad',           'Copia de la escritura de propiedad o contrato de arrendamiento', 50),
    ('plano_mensura',            'Plano de Mensura',                 'Plano de mensura certificado por agrimensor licenciado', 60),
    ('certificacion_deuda_crim', 'Certificacion de Deuda CRIM',      'Certificacion negativa de deuda del CRIM', 70),
    ('certificacion_hacienda',   'Certificacion de Hacienda',        'Certificacion de radicacion de planillas', 80),
    ('certificacion_asume',      'Certificacion de ASUME',           'Certificacion de cumplimiento de pension alimentaria', 90),
    ('desconocido',              'Desconocido',                      'No corresponde claramente a ninguna categoria', 999)
  ) AS d(code, name, description, sort_order)
 WHERE r.permit_type = 'documentos_generales' AND r.version = 'dg-2026.1'
ON CONFLICT (ruleset_id, code) DO NOTHING;


-- -----------------------------------------------------------------------------
-- Point San Juan at the new baseline. Existing cases keep their old stamp -
-- cases.ruleset_version_id is immutable by trigger, which is the point.
-- -----------------------------------------------------------------------------

UPDATE organizations o
   SET active_ruleset_id = r.id
  FROM rulesets r
 WHERE r.permit_type = 'permiso_unico'
   AND r.version = 'pu-2026.1'
   AND o.municipality = 'San Juan';

-- =============================================================================
-- DONE. Rule bodies (the 28 seed rules) arrive in 007.
-- =============================================================================
