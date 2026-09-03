-- =============================================================================
-- PYXTEN 008 - APPLICANT PROFILE AND FILING DATE ON A CASE
--
-- Additive. Two columns the seeded rules already reference.
--
-- `profile` answers the questions that decide which rules apply at all:
--     forma_juridica       persona_natural | entidad_juridica
--     tenencia             dueno | arrendatario
--     tipo_tramite         nueva | renovacion
--     categoria_uso        alimentos | salud | comercio_general | entretenimiento | industrial
--     acceso_publico       true | false
--     radica_representante true | false
--
-- Deliberately jsonb rather than six columns: the profile is configuration that
-- follows the ruleset, and San Juan's intake form may not capture exactly these.
-- An unanswered key is NOT treated as "no" - the evaluator returns UNKNOWN and
-- the affected rule escalates to a reviewer, which is why leaving this empty is
-- safe rather than silently wrong.
--
-- `filing_date` is what validity is measured against. It defaults to the day the
-- case was opened, which is right for over-the-counter intake and can be set
-- explicitly for a package that arrived earlier.
-- =============================================================================

ALTER TABLE cases ADD COLUMN IF NOT EXISTS profile JSONB NOT NULL DEFAULT '{}'::jsonb;
ALTER TABLE cases ADD COLUMN IF NOT EXISTS filing_date DATE;

UPDATE cases SET filing_date = created_at::date WHERE filing_date IS NULL;

ALTER TABLE cases ALTER COLUMN filing_date SET DEFAULT CURRENT_DATE;

-- =============================================================================
-- DONE.
-- =============================================================================
