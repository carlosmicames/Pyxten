-- =============================================================================
-- PYXTEN FOLDERS MIGRATION
-- Run this SQL in your Supabase SQL Editor
-- =============================================================================

-- =============================================================================
-- 1. CREATE FOLDERS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS folders (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    name TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraint: prevent duplicate folder names per user (case-insensitive)
CREATE UNIQUE INDEX IF NOT EXISTS idx_folders_user_name_unique
ON folders (user_id, LOWER(name));

-- Index for faster queries by user_id
CREATE INDEX IF NOT EXISTS idx_folders_user_id ON folders(user_id);
CREATE INDEX IF NOT EXISTS idx_folders_created_at ON folders(created_at DESC);

-- =============================================================================
-- 2. CREATE FOLDER_ITEMS TABLE
-- =============================================================================

CREATE TABLE IF NOT EXISTS folder_items (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE NOT NULL,
    folder_id UUID REFERENCES folders(id) ON DELETE CASCADE NOT NULL,
    validation_id UUID REFERENCES validations(id) ON DELETE CASCADE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Unique constraint: prevent duplicate validation in same folder
CREATE UNIQUE INDEX IF NOT EXISTS idx_folder_items_folder_validation_unique
ON folder_items (folder_id, validation_id);

-- Indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_folder_items_user_id ON folder_items(user_id);
CREATE INDEX IF NOT EXISTS idx_folder_items_folder_id ON folder_items(folder_id);
CREATE INDEX IF NOT EXISTS idx_folder_items_validation_id ON folder_items(validation_id);
CREATE INDEX IF NOT EXISTS idx_folder_items_created_at ON folder_items(created_at DESC);

-- =============================================================================
-- 3. ENABLE ROW LEVEL SECURITY
-- =============================================================================

ALTER TABLE folders ENABLE ROW LEVEL SECURITY;
ALTER TABLE folder_items ENABLE ROW LEVEL SECURITY;

-- =============================================================================
-- 4. DROP EXISTING POLICIES (for clean reinstall)
-- =============================================================================

DROP POLICY IF EXISTS "Users can view own folders" ON folders;
DROP POLICY IF EXISTS "Users can insert own folders" ON folders;
DROP POLICY IF EXISTS "Users can update own folders" ON folders;
DROP POLICY IF EXISTS "Users can delete own folders" ON folders;

DROP POLICY IF EXISTS "Users can view own folder items" ON folder_items;
DROP POLICY IF EXISTS "Users can insert own folder items" ON folder_items;
DROP POLICY IF EXISTS "Users can delete own folder items" ON folder_items;

-- =============================================================================
-- 5. FOLDERS TABLE POLICIES
-- =============================================================================

-- Users can only SELECT their own folders
CREATE POLICY "Users can view own folders"
ON folders FOR SELECT
USING (auth.uid() = user_id);

-- Users can only INSERT folders with their own user_id
CREATE POLICY "Users can insert own folders"
ON folders FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can only UPDATE their own folders
CREATE POLICY "Users can update own folders"
ON folders FOR UPDATE
USING (auth.uid() = user_id)
WITH CHECK (auth.uid() = user_id);

-- Users can only DELETE their own folders
CREATE POLICY "Users can delete own folders"
ON folders FOR DELETE
USING (auth.uid() = user_id);

-- =============================================================================
-- 6. FOLDER_ITEMS TABLE POLICIES
-- =============================================================================

-- Users can only SELECT their own folder items
CREATE POLICY "Users can view own folder items"
ON folder_items FOR SELECT
USING (auth.uid() = user_id);

-- Users can only INSERT folder items with their own user_id
CREATE POLICY "Users can insert own folder items"
ON folder_items FOR INSERT
WITH CHECK (auth.uid() = user_id);

-- Users can only DELETE their own folder items
CREATE POLICY "Users can delete own folder items"
ON folder_items FOR DELETE
USING (auth.uid() = user_id);

-- =============================================================================
-- 7. ADD phase1_result COLUMN TO PROJECTS (if not exists)
-- =============================================================================

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'projects' AND column_name = 'phase1_result'
    ) THEN
        ALTER TABLE projects ADD COLUMN phase1_result JSONB;
    END IF;
END $$;

-- =============================================================================
-- DONE! Folders tables are now configured.
-- =============================================================================
