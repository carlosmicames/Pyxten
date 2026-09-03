-- =============================================================================
-- PYXTEN 009 - USE MAPPINGS AND THE ZONING RULE
--
-- Additive. Run after 008. Idempotent.
--
-- WHY THIS TABLE EXISTS
--   Deciding that "panaderia" is COM-RETAIL is a classification, and on the
--   applicant side a model does it. On the reviewer side it is data: a keyword
--   table a municipality can read, audit and edit, versioned with the ruleset
--   like every other rule input.
--
--   An activity that matches no keyword - or more than one - does NOT get a
--   best guess. The wrapper records `ambiguo` and the rule escalates to the
--   reviewer with the declared activity shown.
--
-- WHY A-01 CHANGES SHAPE
--   As seeded in 007 it used `external_agrees`, which compares two strings.
--   Zoning compatibility is not a string comparison: it is a coordinate lookup,
--   a POT-to-RC mapping and a table check. The wrapper performs that and records
--   the outcome; the rule now reads it with `external_matched`.
-- =============================================================================


-- =============================================================================
-- 1. USE MAPPINGS
-- =============================================================================

CREATE TABLE IF NOT EXISTS use_mappings (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ruleset_id UUID NOT NULL REFERENCES rulesets(id) ON DELETE CASCADE,
    use_code   TEXT NOT NULL,
    -- Lowercase, unaccented substrings matched against the declared activity.
    keywords   TEXT[] NOT NULL DEFAULT '{}',
    notes      TEXT,
    UNIQUE (ruleset_id, use_code)
);

CREATE INDEX IF NOT EXISTS idx_use_mappings_ruleset ON use_mappings(ruleset_id);

ALTER TABLE use_mappings ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS use_mappings_read ON use_mappings;
CREATE POLICY use_mappings_read ON use_mappings FOR SELECT TO authenticated USING (TRUE);


-- =============================================================================
-- 2. SEED - keyed to the use codes in api/app/services/rules_data.py
--
-- Coverage here is deliberately narrow. A keyword list that tries to catch
-- everything produces confident wrong mappings; one that catches the common
-- cases and escalates the rest produces reviewable ones. Extend it from real
-- patentes rather than from imagination.
-- =============================================================================

INSERT INTO use_mappings (ruleset_id, use_code, keywords, notes)
SELECT r.id, m.use_code, m.keywords, m.notes
  FROM rulesets r
  CROSS JOIN (VALUES
    ('COM-RETAIL', ARRAY['panaderia','reposteria','colmado','supermercado','farmacia',
                         'ferreteria','tienda','boutique','floristeria','libreria',
                         'venta al detal','lavanderia','barberia','salon de belleza'],
     'Venta al detal y servicios personales'),

    ('COM-RESTAURANT', ARRAY['restaurante','cafeteria','cafe','fonda','pizzeria',
                             'comida rapida','food truck','bar','cantina'],
     'Requiere ademas certificado de salud'),

    ('COM-OFFICE', ARRAY['oficina','consultorio','bufete','despacho','contabilidad',
                         'agencia de seguros','bienes raices'],
     'Oficina profesional o administrativa'),

    ('COM-WAREHOUSE', ARRAY['almacen','deposito','bodega','centro de distribucion'],
     NULL),

    ('IND-LIGHT', ARRAY['manufactura liviana','ensamblaje','taller de produccion',
                        'imprenta','carpinteria'],
     NULL),

    ('IND-HEAVY', ARRAY['manufactura pesada','planta industrial','fundicion'],
     NULL),

    ('TOURIST-HOTEL', ARRAY['hotel','hospedaje','paradore','parador','airbnb',
                            'alquiler a corto plazo','posada'],
     NULL),

    ('RES-MF', ARRAY['apartamentos','multifamiliar','walk-up'], NULL),

    ('RES-SF', ARRAY['residencia unifamiliar','vivienda unifamiliar'], NULL)
  ) AS m(use_code, keywords, notes)
 WHERE r.permit_type = 'permiso_unico' AND r.version = 'pu-2026.1'
ON CONFLICT (ruleset_id, use_code) DO NOTHING;


-- =============================================================================
-- 3. A-01 - rewritten and enabled
--
-- pass:   the recorded determination says the use is compatible
-- fail:   it says it is not
-- review: no determination, or one flagged ambiguous / offline / unexpected -
--         which `external_matched` returns as unknown, so both pass and fail
--         come out unknown and the engine escalates on its own. No explicit
--         review_condition is needed, and adding one would double-count.
--
-- Note what this rule can and cannot do. A GIS outage, a point that falls
-- between parcels, an unmapped POT district and an unrecognised activity all
-- reach the reviewer. None of them can produce "compatible".
-- =============================================================================

UPDATE rules ru
   SET pass_condition   = '{"external_matched": {"source": "zonificacion"}}'::jsonb,
       fail_condition   = '{"not": {"external_matched": {"source": "zonificacion"}}}'::jsonb,
       review_condition = NULL,
       enabled          = TRUE,
       title            = 'Uso declarado compatible con la calificacion del predio'
  FROM rulesets rs
 WHERE rs.id = ru.ruleset_id
   AND rs.permit_type = 'permiso_unico'
   AND rs.version = 'pu-2026.1'
   AND ru.code = 'A-01';


-- =============================================================================
-- VERIFY
-- =============================================================================

DO $$
DECLARE
    mapped INTEGER;
    zoning_enabled BOOLEAN;
BEGIN
    SELECT COUNT(*) INTO mapped
      FROM use_mappings um
      JOIN rulesets rs ON rs.id = um.ruleset_id
     WHERE rs.permit_type = 'permiso_unico' AND rs.version = 'pu-2026.1';

    SELECT ru.enabled INTO zoning_enabled
      FROM rules ru
      JOIN rulesets rs ON rs.id = ru.ruleset_id
     WHERE rs.permit_type = 'permiso_unico' AND rs.version = 'pu-2026.1'
       AND ru.code = 'A-01';

    RAISE NOTICE 'Mapeos de uso: % | A-01 habilitada: %', mapped, zoning_enabled;
END $$;

-- =============================================================================
-- DONE.
-- =============================================================================
