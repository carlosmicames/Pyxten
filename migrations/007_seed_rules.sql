-- =============================================================================
-- PYXTEN 007 - SEED RULES for the Permiso Unico baseline ruleset
--
-- Rules are data. Nothing in this file is logic; it is thirty-one rows that the
-- deterministic evaluator in api/app/reviewer/rules/ reads.
--
-- Run after 006. Idempotent.
--
-- ON CITATIONS - READ THIS BEFORE ISSUING A NOTICE
--   Every rule below cites "Reglamento Conjunto 2023" or the DRNA order, which
--   is true and verifiable. None of them cites an article or section number,
--   because I do not have the RC text and a fabricated section reference in a
--   signed requerimiento is worse than no reference at all. Before findings from
--   these rules go into an issued notice, fill in `rules.citation` with the
--   specific article for each. That is an UPDATE per rule, no code change.
--
-- ON VALIDITY PERIODS
--   No rule computes an expiry from an issue date plus a period, because I do
--   not have those periods. Every validity rule reads the expiration date the
--   certification carries and escalates when that date is absent or illegible.
--   If San Juan confirms fixed periods, those become additional rules.
--
-- FIELD KEYS
--   Conditions reference facts as `<document_type>.<field>`. This file is
--   therefore also the specification of what fact extraction must produce.
-- =============================================================================

INSERT INTO rules (
    ruleset_id, code, title, family, authority, citation,
    applies_when, required_evidence, pass_condition, fail_condition, review_condition,
    severity, enabled
)
SELECT r.id, v.code, v.title, v.family, v.authority, v.citation,
       v.applies_when::jsonb, v.required_evidence::jsonb,
       v.pass_condition::jsonb, v.fail_condition::jsonb, v.review_condition::jsonb,
       v.severity, v.enabled
  FROM rulesets r
  CROSS JOIN (VALUES

-- =============================================================================
-- FAMILIA: PRESENCIA
-- Does the required document exist for this applicant profile?
--
-- The evidence for an absence is the inventory: these are the documents that
-- were filed, and none of them is the one required.
-- =============================================================================

('P-01', 'Registro de comerciante presente', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 NULL,
 '["registro_comerciante"]',
 '{"doc_present": {"type": "registro_comerciante"}}',
 '{"not": {"doc_present": {"type": "registro_comerciante"}}}',
 NULL, 'grave', TRUE),

('P-02', 'Patente municipal presente', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 NULL,
 '["patente_municipal"]',
 '{"doc_present": {"type": "patente_municipal"}}',
 '{"not": {"doc_present": {"type": "patente_municipal"}}}',
 NULL, 'grave', TRUE),

('P-03', 'Certificacion del CRIM presente', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 NULL,
 '["certificacion_crim"]',
 '{"doc_present": {"type": "certificacion_crim"}}',
 '{"not": {"doc_present": {"type": "certificacion_crim"}}}',
 NULL, 'grave', TRUE),

('P-04', 'Certificacion de ASUME presente', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 NULL,
 '["certificacion_asume"]',
 '{"doc_present": {"type": "certificacion_asume"}}',
 '{"not": {"doc_present": {"type": "certificacion_asume"}}}',
 NULL, 'grave', TRUE),

('P-05', 'Certificado de bomberos presente', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 NULL,
 '["certificado_bomberos"]',
 '{"doc_present": {"type": "certificado_bomberos"}}',
 '{"not": {"doc_present": {"type": "certificado_bomberos"}}}',
 NULL, 'grave', TRUE),

-- Conditional on the use. An unanswered profile question makes the rule's own
-- applicability unknown, which escalates rather than silently skipping.
('P-06', 'Certificado de salud presente cuando el uso lo requiere', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"any": [{"profile_is": {"key": "categoria_uso", "value": "alimentos"}},
           {"profile_is": {"key": "categoria_uso", "value": "salud"}}]}',
 '["certificado_salud"]',
 '{"doc_present": {"type": "certificado_salud"}}',
 '{"not": {"doc_present": {"type": "certificado_salud"}}}',
 NULL, 'grave', TRUE),

-- Title is proved by either instrument; one of the two suffices.
('P-07', 'Titularidad o arrendamiento acreditado', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 NULL,
 '["escritura_titularidad", "contrato_arrendamiento"]',
 '{"any": [{"doc_present": {"type": "escritura_titularidad"}},
           {"doc_present": {"type": "contrato_arrendamiento"}}]}',
 '{"not": {"any": [{"doc_present": {"type": "escritura_titularidad"}},
                   {"doc_present": {"type": "contrato_arrendamiento"}}]}}',
 NULL, 'grave', TRUE),

('P-08', 'Plano de distribucion presente', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 NULL,
 '["plano_distribucion"]',
 '{"doc_present": {"type": "plano_distribucion"}}',
 '{"not": {"doc_present": {"type": "plano_distribucion"}}}',
 NULL, 'moderada', TRUE),

('P-09', 'Certificacion ADA presente en local de acceso publico', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"profile_is": {"key": "acceso_publico", "value": true}}',
 '["certificacion_ada"]',
 '{"doc_present": {"type": "certificacion_ada"}}',
 '{"not": {"doc_present": {"type": "certificacion_ada"}}}',
 NULL, 'moderada', TRUE),

('P-10', 'Poder de representacion cuando no radica el solicitante', 'presencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"profile_is": {"key": "radica_representante", "value": true}}',
 '["poder_representacion"]',
 '{"doc_present": {"type": "poder_representacion"}}',
 '{"not": {"doc_present": {"type": "poder_representacion"}}}',
 NULL, 'grave', TRUE),

-- Never a finding against the applicant: an unclassified document is our
-- uncertainty, not their deficiency. No fail_condition, so no citation needed -
-- which is the rules_finding_requires_citation constraint doing its job.
('P-11', 'No quedan documentos sin clasificar en el expediente', 'presencia', 'INTERNO', NULL,
 NULL,
 '[]',
 '{"not": {"doc_present": {"type": "desconocido"}}}',
 NULL,
 '{"doc_present": {"type": "desconocido"}}',
 'leve', TRUE),


-- =============================================================================
-- FAMILIA: VIGENCIA
-- Is the document current as of the filing date, and did the expected entity
-- issue it? Each rule applies only when the document is actually present -
-- absence is the presence family's business.
-- =============================================================================

('V-01', 'Certificacion del CRIM vigente a la fecha de radicacion', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "certificacion_crim"}}',
 '["certificacion_crim"]',
 '{"date_on_or_after": {"field": "certificacion_crim.fecha_vencimiento", "reference": "case.filing_date"}}',
 '{"not": {"date_on_or_after": {"field": "certificacion_crim.fecha_vencimiento", "reference": "case.filing_date"}}}',
 '{"not": {"field_present": {"field": "certificacion_crim.fecha_vencimiento"}}}',
 'grave', TRUE),

('V-02', 'Certificacion de ASUME vigente a la fecha de radicacion', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "certificacion_asume"}}',
 '["certificacion_asume"]',
 '{"date_on_or_after": {"field": "certificacion_asume.fecha_vencimiento", "reference": "case.filing_date"}}',
 '{"not": {"date_on_or_after": {"field": "certificacion_asume.fecha_vencimiento", "reference": "case.filing_date"}}}',
 '{"not": {"field_present": {"field": "certificacion_asume.fecha_vencimiento"}}}',
 'grave', TRUE),

('V-03', 'Certificado de bomberos vigente a la fecha de radicacion', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "certificado_bomberos"}}',
 '["certificado_bomberos"]',
 '{"date_on_or_after": {"field": "certificado_bomberos.fecha_vencimiento", "reference": "case.filing_date"}}',
 '{"not": {"date_on_or_after": {"field": "certificado_bomberos.fecha_vencimiento", "reference": "case.filing_date"}}}',
 '{"not": {"field_present": {"field": "certificado_bomberos.fecha_vencimiento"}}}',
 'grave', TRUE),

('V-04', 'Certificado de salud vigente a la fecha de radicacion', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "certificado_salud"}}',
 '["certificado_salud"]',
 '{"date_on_or_after": {"field": "certificado_salud.fecha_vencimiento", "reference": "case.filing_date"}}',
 '{"not": {"date_on_or_after": {"field": "certificado_salud.fecha_vencimiento", "reference": "case.filing_date"}}}',
 '{"not": {"field_present": {"field": "certificado_salud.fecha_vencimiento"}}}',
 'grave', TRUE),

('V-05', 'Patente municipal cubre la fecha de radicacion', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "patente_municipal"}}',
 '["patente_municipal"]',
 '{"date_on_or_after": {"field": "patente_municipal.periodo_hasta", "reference": "case.filing_date"}}',
 '{"not": {"date_on_or_after": {"field": "patente_municipal.periodo_hasta", "reference": "case.filing_date"}}}',
 '{"not": {"field_present": {"field": "patente_municipal.periodo_hasta"}}}',
 'grave', TRUE),

('V-06', 'Registro de comerciante en estatus activo', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "registro_comerciante"}}',
 '["registro_comerciante"]',
 '{"field_contains": {"field": "registro_comerciante.estatus", "keywords": ["activo", "vigente"]}}',
 '{"field_contains": {"field": "registro_comerciante.estatus", "keywords": ["inactivo", "revocado", "cancelado", "suspendido"]}}',
 '{"not": {"field_present": {"field": "registro_comerciante.estatus"}}}',
 'grave', TRUE),

('V-07', 'Contrato de arrendamiento vigente a la fecha de radicacion', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"all": [{"profile_is": {"key": "tenencia", "value": "arrendatario"}},
           {"doc_present": {"type": "contrato_arrendamiento"}}]}',
 '["contrato_arrendamiento"]',
 '{"date_on_or_after": {"field": "contrato_arrendamiento.vigencia_hasta", "reference": "case.filing_date"}}',
 '{"not": {"date_on_or_after": {"field": "contrato_arrendamiento.vigencia_hasta", "reference": "case.filing_date"}}}',
 '{"not": {"field_present": {"field": "contrato_arrendamiento.vigencia_hasta"}}}',
 'grave', TRUE),

('V-08', 'Certificacion del CRIM emitida por el CRIM', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "certificacion_crim"}}',
 '["certificacion_crim"]',
 '{"issued_by": {"field": "certificacion_crim.entidad_emisora", "keywords": ["crim", "centro de recaudacion de ingresos municipales"]}}',
 '{"not": {"issued_by": {"field": "certificacion_crim.entidad_emisora", "keywords": ["crim", "centro de recaudacion de ingresos municipales"]}}}',
 '{"not": {"field_present": {"field": "certificacion_crim.entidad_emisora"}}}',
 'moderada', TRUE),

('V-09', 'Certificacion de ASUME emitida por ASUME', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "certificacion_asume"}}',
 '["certificacion_asume"]',
 '{"issued_by": {"field": "certificacion_asume.entidad_emisora", "keywords": ["asume", "administracion para el sustento de menores"]}}',
 '{"not": {"issued_by": {"field": "certificacion_asume.entidad_emisora", "keywords": ["asume", "administracion para el sustento de menores"]}}}',
 '{"not": {"field_present": {"field": "certificacion_asume.entidad_emisora"}}}',
 'moderada', TRUE),

('V-10', 'Certificado de bomberos emitido por el Negociado del Cuerpo de Bomberos', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "certificado_bomberos"}}',
 '["certificado_bomberos"]',
 '{"issued_by": {"field": "certificado_bomberos.entidad_emisora", "keywords": ["bomberos", "negociado del cuerpo de bomberos"]}}',
 '{"not": {"issued_by": {"field": "certificado_bomberos.entidad_emisora", "keywords": ["bomberos", "negociado del cuerpo de bomberos"]}}}',
 '{"not": {"field_present": {"field": "certificado_bomberos.entidad_emisora"}}}',
 'moderada', TRUE),

('V-11', 'Plano de distribucion firmado por profesional autorizado', 'vigencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "plano_distribucion"}}',
 '["plano_distribucion"]',
 '{"all": [{"field_present": {"field": "plano_distribucion.profesional_autorizado"}},
           {"field_present": {"field": "plano_distribucion.numero_licencia"}}]}',
 NULL,
 '{"not": {"all": [{"field_present": {"field": "plano_distribucion.profesional_autorizado"}},
                   {"field_present": {"field": "plano_distribucion.numero_licencia"}}]}}',
 'moderada', TRUE),


-- =============================================================================
-- FAMILIA: CONSISTENCIA
--
-- Where most real deficiencies live, and where a wrong finding is most likely.
-- Note the shape of every rule here: `fail` is the negation of `pass`, and the
-- comparators return three values - so a plausible naming variant produces
-- neither a pass nor a fail and falls through to requiere_criterio with both
-- values shown. Only a substantive difference reaches the applicant as a
-- finding, and the engine will not let it do so without citing both documents.
-- =============================================================================

('C-01', 'Nombre del solicitante concuerda entre registro y patente', 'consistencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"all": [{"doc_present": {"type": "registro_comerciante"}},
           {"doc_present": {"type": "patente_municipal"}}]}',
 '["registro_comerciante", "patente_municipal"]',
 '{"field_equals": {"left": "registro_comerciante.nombre_solicitante", "right": "patente_municipal.nombre_solicitante", "normalize": "entity_name"}}',
 '{"not": {"field_equals": {"left": "registro_comerciante.nombre_solicitante", "right": "patente_municipal.nombre_solicitante", "normalize": "entity_name"}}}',
 NULL, 'moderada', TRUE),

('C-02', 'Nombre en la certificacion del CRIM concuerda con el solicitante (persona natural)', 'consistencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"all": [{"profile_is": {"key": "forma_juridica", "value": "persona_natural"}},
           {"doc_present": {"type": "certificacion_crim"}},
           {"doc_present": {"type": "patente_municipal"}}]}',
 '["certificacion_crim", "patente_municipal"]',
 '{"field_equals": {"left": "certificacion_crim.nombre_solicitante", "right": "patente_municipal.nombre_solicitante", "normalize": "person_name"}}',
 '{"not": {"field_equals": {"left": "certificacion_crim.nombre_solicitante", "right": "patente_municipal.nombre_solicitante", "normalize": "person_name"}}}',
 NULL, 'moderada', TRUE),

('C-03', 'Nombre en la certificacion de ASUME concuerda con el solicitante (persona natural)', 'consistencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"all": [{"profile_is": {"key": "forma_juridica", "value": "persona_natural"}},
           {"doc_present": {"type": "certificacion_asume"}},
           {"doc_present": {"type": "patente_municipal"}}]}',
 '["certificacion_asume", "patente_municipal"]',
 '{"field_equals": {"left": "certificacion_asume.nombre_solicitante", "right": "patente_municipal.nombre_solicitante", "normalize": "person_name"}}',
 '{"not": {"field_equals": {"left": "certificacion_asume.nombre_solicitante", "right": "patente_municipal.nombre_solicitante", "normalize": "person_name"}}}',
 NULL, 'moderada', TRUE),

-- Compares two FILED documents, not a document against the case record. A
-- mismatch with what a clerk typed into the expediente is a data-entry question,
-- not an applicant deficiency, and the engine would refuse to make it a finding
-- anyway: a contradiction claim has to cite two documents.
('C-04', 'Catastro concuerda entre la escritura y la certificacion del CRIM', 'consistencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"all": [{"doc_present": {"type": "escritura_titularidad"}},
           {"doc_present": {"type": "certificacion_crim"}}]}',
 '["escritura_titularidad", "certificacion_crim"]',
 '{"field_equals": {"left": "escritura_titularidad.catastro", "right": "certificacion_crim.catastro", "normalize": "catastro"}}',
 '{"not": {"field_equals": {"left": "escritura_titularidad.catastro", "right": "certificacion_crim.catastro", "normalize": "catastro"}}}',
 NULL, 'grave', TRUE),

('C-05', 'Direccion del negocio concuerda entre la patente y el certificado de bomberos', 'consistencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"all": [{"doc_present": {"type": "patente_municipal"}},
           {"doc_present": {"type": "certificado_bomberos"}}]}',
 '["patente_municipal", "certificado_bomberos"]',
 '{"field_equals": {"left": "patente_municipal.direccion_negocio", "right": "certificado_bomberos.direccion_negocio", "normalize": "address"}}',
 '{"not": {"field_equals": {"left": "patente_municipal.direccion_negocio", "right": "certificado_bomberos.direccion_negocio", "normalize": "address"}}}',
 NULL, 'moderada', TRUE),

-- The lessor has to be the person the deed says owns the property.
('C-06', 'El arrendador del contrato es el titular de la escritura', 'consistencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"all": [{"doc_present": {"type": "contrato_arrendamiento"}},
           {"doc_present": {"type": "escritura_titularidad"}}]}',
 '["contrato_arrendamiento", "escritura_titularidad"]',
 '{"field_equals": {"left": "contrato_arrendamiento.arrendador", "right": "escritura_titularidad.titular", "normalize": "person_name"}}',
 '{"not": {"field_equals": {"left": "contrato_arrendamiento.arrendador", "right": "escritura_titularidad.titular", "normalize": "person_name"}}}',
 NULL, 'grave', TRUE),

('C-07', 'Nombre comercial concuerda entre registro y patente', 'consistencia', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"all": [{"doc_present": {"type": "registro_comerciante"}},
           {"doc_present": {"type": "patente_municipal"}}]}',
 '["registro_comerciante", "patente_municipal"]',
 '{"field_equals": {"left": "registro_comerciante.nombre_comercial", "right": "patente_municipal.nombre_comercial", "normalize": "entity_name"}}',
 '{"not": {"field_equals": {"left": "registro_comerciante.nombre_comercial", "right": "patente_municipal.nombre_comercial", "normalize": "entity_name"}}}',
 NULL, 'leve', TRUE),

-- The declared activity drives which endorsements are required, so a mismatch
-- here can invalidate the rest of the review. Escalates only - a difference in
-- wording between two forms is not by itself a deficiency.
('C-08', 'Actividad declarada concuerda entre registro y patente', 'consistencia', 'INTERNO', NULL,
 '{"all": [{"doc_present": {"type": "registro_comerciante"}},
           {"doc_present": {"type": "patente_municipal"}}]}',
 '["registro_comerciante", "patente_municipal"]',
 '{"field_equals": {"left": "registro_comerciante.actividad", "right": "patente_municipal.actividad", "normalize": "exact"}}',
 NULL,
 '{"not": {"field_equals": {"left": "registro_comerciante.actividad", "right": "patente_municipal.actividad", "normalize": "exact"}}}',
 'leve', TRUE),


-- =============================================================================
-- FAMILIA: APLICABILIDAD
--
-- Disabled until the GIS wrapper lands. A rule that escalates on every single
-- case teaches reviewers to ignore escalations, which is the one thing this
-- product cannot afford. Enable with:
--   UPDATE rules SET enabled = TRUE WHERE code = 'A-01';
-- =============================================================================

('A-01', 'Uso propuesto compatible con la calificacion del predio', 'aplicabilidad', 'RC-2023', 'Reglamento Conjunto 2023',
 '{"doc_present": {"type": "patente_municipal"}}',
 '["patente_municipal"]',
 '{"external_agrees": {"source": "mipr_calificacion", "field": "patente_municipal.actividad", "normalize": "exact"}}',
 NULL,
 '{"not": {"external_agrees": {"source": "mipr_calificacion", "field": "patente_municipal.actividad", "normalize": "exact"}}}',
 'grave', FALSE)

  ) AS v(code, title, family, authority, citation,
         applies_when, required_evidence, pass_condition, fail_condition, review_condition,
         severity, enabled)
 WHERE r.permit_type = 'permiso_unico' AND r.version = 'pu-2026.1'
ON CONFLICT (ruleset_id, code) DO NOTHING;


-- =============================================================================
-- VERIFY
-- =============================================================================

DO $$
DECLARE
    seeded INTEGER;
BEGIN
    SELECT COUNT(*) INTO seeded
      FROM rules ru
      JOIN rulesets rs ON rs.id = ru.ruleset_id
     WHERE rs.permit_type = 'permiso_unico' AND rs.version = 'pu-2026.1';

    RAISE NOTICE 'Reglas sembradas para pu-2026.1: %', seeded;
END $$;

-- =============================================================================
-- DONE. 31 rules: 11 presencia, 11 vigencia, 8 consistencia, 1 aplicabilidad
-- (disabled). Next: fact extraction, which must produce the field keys these
-- conditions reference.
-- =============================================================================
