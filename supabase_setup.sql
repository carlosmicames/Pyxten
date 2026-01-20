-- =============================================================================
-- PYXTEN SUPABASE SETUP
-- Run this SQL in your Supabase SQL Editor
-- =============================================================================

-- =============================================================================
-- 1. ALTER TABLE: Add missing columns to validations table
-- (Run only if columns don't exist - check first)
-- =============================================================================

-- Add project_description column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'validations' AND column_name = 'project_description'
    ) THEN
        ALTER TABLE validations ADD COLUMN project_description TEXT;
    END IF;
END $$;

-- Add property_address column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'validations' AND column_name = 'property_address'
    ) THEN
        ALTER TABLE validations ADD COLUMN property_address TEXT;
    END IF;
END $$;

-- Add municipality column if it doesn't exist
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'validations' AND column_name = 'municipality'
    ) THEN
        ALTER TABLE validations ADD COLUMN municipality TEXT;
    END IF;
END $$;

-- =============================================================================
-- 2. ROW LEVEL SECURITY (RLS) POLICIES
-- Ensures users can only access their own data
-- =============================================================================

-- Enable RLS on all tables
ALTER TABLE projects ENABLE ROW LEVEL SECURITY;
ALTER TABLE validations ENABLE ROW LEVEL SECURITY;
ALTER TABLE usage_tracking ENABLE ROW LEVEL SECURITY;

-- Drop existing policies if they exist (for clean reinstall)
DROP POLICY IF EXISTS "Users can view own projects" ON projects;
DROP POLICY IF EXISTS "Users can insert own projects" ON projects;
DROP POLICY IF EXISTS "Users can update own projects" ON projects;
DROP POLICY IF EXISTS "Users can delete own projects" ON projects;

DROP POLICY IF EXISTS "Users can view own validations" ON validations;
DROP POLICY IF EXISTS "Users can insert own validations" ON validations;

DROP POLICY IF EXISTS "Users can view own usage" ON usage_tracking;
DROP POLICY IF EXISTS "Users can insert own usage" ON usage_tracking;
DROP POLICY IF EXISTS "Users can update own usage" ON usage_tracking;

-- -----------------------------------------------------------------------------
-- PROJECTS TABLE POLICIES
-- -----------------------------------------------------------------------------

-- Users can only SELECT their own projects
CREATE POLICY "Users can view own projects"
ON projects FOR SELECT
USING (auth.uid() = user_id);

-- Users can only INSERT projects with their own user_id
CREATE POLICY "Users can insert own projects"
ON projects FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can only UPDATE their own projects
CREATE POLICY "Users can update own projects"
ON projects FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can only DELETE their own projects
CREATE POLICY "Users can delete own projects"
ON projects FOR DELETE
USING (auth.uid() = user_id);

-- -----------------------------------------------------------------------------
-- VALIDATIONS TABLE POLICIES
-- -----------------------------------------------------------------------------

-- Users can only SELECT their own validations
CREATE POLICY "Users can view own validations"
ON validations FOR SELECT
USING (auth.uid() = user_id);

-- Users can only INSERT validations with their own user_id
CREATE POLICY "Users can insert own validations"
ON validations FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- -----------------------------------------------------------------------------
-- USAGE_TRACKING TABLE POLICIES
-- -----------------------------------------------------------------------------

-- Users can only SELECT their own usage records
CREATE POLICY "Users can view own usage"
ON usage_tracking FOR SELECT
USING (auth.uid() = user_id);

-- Users can only INSERT usage records with their own user_id
CREATE POLICY "Users can insert own usage"
ON usage_tracking FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can only UPDATE their own usage records
CREATE POLICY "Users can update own usage"
ON usage_tracking FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- =============================================================================
-- 3. CREATE TABLES (if they don't exist)
-- Only run if tables are missing
-- =============================================================================

-- Projects table
CREATE TABLE IF NOT EXISTS projects (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    address TEXT,
    municipality TEXT,
    catastro_number TEXT,
    calificacion TEXT,
    zoning_code TEXT,
    status TEXT DEFAULT 'En Progreso',
    phase1_completed BOOLEAN DEFAULT FALSE,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- Validations table
CREATE TABLE IF NOT EXISTS validations (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    project_id UUID REFERENCES projects(id) ON DELETE SET NULL,
    validation_type TEXT NOT NULL DEFAULT 'fase1',
    result JSONB NOT NULL,
    viable BOOLEAN DEFAULT FALSE,
    project_description TEXT,
    property_address TEXT,
    municipality TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Usage tracking table
CREATE TABLE IF NOT EXISTS usage_tracking (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    period TEXT NOT NULL,
    validations_used INTEGER DEFAULT 0,
    tier TEXT DEFAULT 'free',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(user_id, period)
);

-- Subscriptions table (optional - for future payment integration)
CREATE TABLE IF NOT EXISTS subscriptions (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    tier TEXT NOT NULL DEFAULT 'free',
    status TEXT DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- =============================================================================
-- 4. INDEXES for better query performance
-- =============================================================================

CREATE INDEX IF NOT EXISTS idx_projects_user_id ON projects(user_id);
CREATE INDEX IF NOT EXISTS idx_projects_created_at ON projects(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_validations_user_id ON validations(user_id);
CREATE INDEX IF NOT EXISTS idx_validations_created_at ON validations(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_usage_tracking_user_period ON usage_tracking(user_id, period);

-- =============================================================================
-- 5. TRIGGER: Auto-update updated_at timestamp on projects
-- =============================================================================

CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

DROP TRIGGER IF EXISTS update_projects_updated_at ON projects;
CREATE TRIGGER update_projects_updated_at
    BEFORE UPDATE ON projects
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- =============================================================================
-- DONE! Your Supabase tables are now configured for multi-user persistence.
-- =============================================================================
