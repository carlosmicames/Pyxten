-- =============================================================================
-- PYXTEN PCOC VALIDATIONS MIGRATION
-- Run this SQL in your Supabase SQL Editor
-- PCOC = Permiso de Construccion (Construction Permit Validation)
-- =============================================================================

-- =============================================================================
-- 1. CREATE PCOC_VALIDATIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS pcoc_validations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,

    -- Basic project info (can be from linked project or manual entry)
    project_name TEXT,
    property_address TEXT,
    municipality TEXT,
    zoning_code TEXT,

    -- Current step in the workflow (1-5: filters 1-4 + result)
    current_step INTEGER DEFAULT 1,
    status TEXT DEFAULT 'en_progreso', -- en_progreso, completado, requiere_accion

    -- Filter 1: Requiere Permiso de Construccion?
    -- Structure: { proposed_use, exempt_selections, ai_interpretation, is_exempt, exempt_reason }
    filter1_data JSONB,

    -- Filter 2: Ubicacion (Zonas Sobrepuestas)
    -- Structure: { zona_historica, zona_turistica, zona_inundacion, auto_detected, user_overrides, required_recommendations }
    filter2_data JSONB,

    -- Filter 3: Clasificacion del Tramite (Ministerial vs Discrecional)
    -- Structure: { project_params, district_requirements, comparison_results, is_ministerial, non_compliant_params }
    filter3_data JSONB,

    -- Filter 4: Cumplimiento Ambiental
    -- Structure: { categorical_exclusion_check, is_categorical_exclusion, exclusion_category, requires_ea_dia }
    filter4_data JSONB,

    -- Final result
    -- Structure: { summary, action_items, recommendations, permit_type, viable }
    result JSONB,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 2. CREATE INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_pcoc_validations_user_id ON pcoc_validations(user_id);
CREATE INDEX IF NOT EXISTS idx_pcoc_validations_project_id ON pcoc_validations(project_id);
CREATE INDEX IF NOT EXISTS idx_pcoc_validations_status ON pcoc_validations(status);
CREATE INDEX IF NOT EXISTS idx_pcoc_validations_created_at ON pcoc_validations(created_at DESC);

-- =============================================================================
-- 3. ENABLE ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE pcoc_validations ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- 4. DROP EXISTING POLICIES (for clean reinstall)
-- =============================================================================

DROP POLICY IF EXISTS "Users can view own pcoc validations" ON pcoc_validations;
DROP POLICY IF EXISTS "Users can insert own pcoc validations" ON pcoc_validations;
DROP POLICY IF EXISTS "Users can update own pcoc validations" ON pcoc_validations;
DROP POLICY IF EXISTS "Users can delete own pcoc validations" ON pcoc_validations;

-- =============================================================================
-- 5. PCOC_VALIDATIONS TABLE POLICIES
-- =============================================================================

-- Users can only SELECT their own PCOC validations
CREATE POLICY "Users can view own pcoc validations"
ON pcoc_validations FOR SELECT
USING (auth.uid() = user_id);

-- Users can only INSERT PCOC validations with their own user_id
CREATE POLICY "Users can insert own pcoc validations"
ON pcoc_validations FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can only UPDATE their own PCOC validations
CREATE POLICY "Users can update own pcoc validations"
ON pcoc_validations FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can only DELETE their own PCOC validations
CREATE POLICY "Users can delete own pcoc validations"
ON pcoc_validations FOR DELETE
USING (auth.uid() = user_id);

-- =============================================================================
-- 6. CREATE TRIGGER FOR updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_pcoc_validations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS pcoc_validations_updated_at ON pcoc_validations;

CREATE TRIGGER pcoc_validations_updated_at
    BEFORE UPDATE ON pcoc_validations
    FOR EACH ROW
    EXECUTE FUNCTION update_pcoc_validations_updated_at();

-- =============================================================================
-- DONE! PCOC validations table is now configured.
-- =============================================================================
