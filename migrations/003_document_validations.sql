-- =============================================================================
-- PYXTEN DOCUMENT VALIDATIONS MIGRATION
-- Run this SQL in your Supabase SQL Editor
-- Document Validation for PCOC and Permiso Unico
-- =============================================================================

-- =============================================================================
-- 1. CREATE DOCUMENT_VALIDATIONS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS document_validations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    pcoc_validation_id UUID REFERENCES pcoc_validations(id) ON DELETE SET NULL,

    -- Validation type: pcoc, permiso_unico
    validation_type TEXT NOT NULL DEFAULT 'pcoc',

    -- Basic project info
    project_name TEXT,
    property_address TEXT,
    municipality TEXT,

    -- Status: en_progreso, completo, requiere_documentos
    status TEXT DEFAULT 'en_progreso',

    -- Documents checklist (JSONB)
    -- Structure: {
    --   "planos_arquitectura": { "required": true, "uploaded": false, "file_url": null, "verified": false, "notes": "" },
    --   "planos_electricos": { "required": true, "uploaded": false, "file_url": null, "verified": false, "notes": "" },
    --   ...
    -- }
    documents JSONB DEFAULT '{}',

    -- Memorial Explicativo (auto-generated content)
    -- Structure: {
    --   "generated": false,
    --   "content": {
    --     "project_description": "",
    --     "location": "",
    --     "zoning_info": "",
    --     "construction_details": "",
    --     "environmental_compliance": "",
    --     "additional_notes": ""
    --   },
    --   "pdf_url": null
    -- }
    memorial_explicativo JSONB DEFAULT '{}',

    -- Additional metadata
    notes TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 2. CREATE INDEXES
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_document_validations_user_id ON document_validations(user_id);
CREATE INDEX IF NOT EXISTS idx_document_validations_pcoc_id ON document_validations(pcoc_validation_id);
CREATE INDEX IF NOT EXISTS idx_document_validations_type ON document_validations(validation_type);
CREATE INDEX IF NOT EXISTS idx_document_validations_status ON document_validations(status);
CREATE INDEX IF NOT EXISTS idx_document_validations_created_at ON document_validations(created_at DESC);

-- =============================================================================
-- 3. ENABLE ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE document_validations ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- 4. DROP EXISTING POLICIES (for clean reinstall)
-- =============================================================================

DROP POLICY IF EXISTS "Users can view own document validations" ON document_validations;
DROP POLICY IF EXISTS "Users can insert own document validations" ON document_validations;
DROP POLICY IF EXISTS "Users can update own document validations" ON document_validations;
DROP POLICY IF EXISTS "Users can delete own document validations" ON document_validations;

-- =============================================================================
-- 5. DOCUMENT_VALIDATIONS TABLE POLICIES
-- =============================================================================

-- Users can only SELECT their own document validations
CREATE POLICY "Users can view own document validations"
ON document_validations FOR SELECT
USING (auth.uid() = user_id);

-- Users can only INSERT document validations with their own user_id
CREATE POLICY "Users can insert own document validations"
ON document_validations FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can only UPDATE their own document validations
CREATE POLICY "Users can update own document validations"
ON document_validations FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can only DELETE their own document validations
CREATE POLICY "Users can delete own document validations"
ON document_validations FOR DELETE
USING (auth.uid() = user_id);

-- =============================================================================
-- 6. CREATE TRIGGER FOR updated_at
-- =============================================================================

CREATE OR REPLACE FUNCTION update_document_validations_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS document_validations_updated_at ON document_validations;

CREATE TRIGGER document_validations_updated_at
    BEFORE UPDATE ON document_validations
    FOR EACH ROW
    EXECUTE FUNCTION update_document_validations_updated_at();

-- =============================================================================
-- 7. CREATE STORAGE BUCKET FOR DOCUMENTS (run separately if needed)
-- =============================================================================
-- Note: This needs to be run in the Supabase Dashboard under Storage
-- INSERT INTO storage.buckets (id, name, public) VALUES ('documents', 'documents', false);
--
-- Then add these policies:
-- CREATE POLICY "Users can upload own documents"
-- ON storage.objects FOR INSERT
-- WITH CHECK (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
--
-- CREATE POLICY "Users can view own documents"
-- ON storage.objects FOR SELECT
-- USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);
--
-- CREATE POLICY "Users can delete own documents"
-- ON storage.objects FOR DELETE
-- USING (bucket_id = 'documents' AND auth.uid()::text = (storage.foldername(name))[1]);

-- =============================================================================
-- DONE! Document validations table is now configured.
-- =============================================================================
