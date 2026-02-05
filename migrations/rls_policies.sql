-- Row-Level Security Policies for Multi-Tenant Isolation
-- Created: 5 Feb 2026
-- 
-- Purpose: Enforce data isolation at PostgreSQL level
-- 
-- How it works:
-- 1. Application sets session variable: SET app.current_producer_id = X
-- 2. RLS policies automatically filter queries using current_setting()
-- 3. Even if application bug, database prevents cross-tenant access
--
-- CRITICAL SECURITY: This is defense-in-depth, not primary security
-- Primary: Application middleware sets context correctly
-- Secondary: RLS prevents bugs/exploits from leaking data

-- ============================================================================
-- ENABLE ROW LEVEL SECURITY ON TENANT-SPECIFIC TABLES
-- ============================================================================

-- Core tables
ALTER TABLE producers ENABLE ROW LEVEL SECURITY;
ALTER TABLE end_customers ENABLE ROW LEVEL SECURITY;
ALTER TABLE machine_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE machine_instances ENABLE ROW LEVEL SECURITY;
ALTER TABLE documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE document_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE queries ENABLE ROW LEVEL SECURITY;

-- User tables (filtered by end_customer → producer)
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_machine_access ENABLE ROW LEVEL SECURITY;

-- Admin tables
ALTER TABLE producer_admins ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- HELPER FUNCTION: Get current producer_id from session
-- ============================================================================

CREATE OR REPLACE FUNCTION get_current_producer_id()
RETURNS INTEGER AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_producer_id', TRUE), '')::INTEGER;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- HELPER FUNCTION: Get current end_customer_id from session
-- ============================================================================

CREATE OR REPLACE FUNCTION get_current_end_customer_id()
RETURNS INTEGER AS $$
BEGIN
    RETURN NULLIF(current_setting('app.current_end_customer_id', TRUE), '')::INTEGER;
EXCEPTION
    WHEN OTHERS THEN
        RETURN NULL;
END;
$$ LANGUAGE plpgsql STABLE;

-- ============================================================================
-- POLICIES: PRODUCERS
-- ============================================================================

-- Producer can only see itself
CREATE POLICY producer_isolation ON producers
    FOR ALL
    USING (id = get_current_producer_id());

-- ============================================================================
-- POLICIES: END_CUSTOMERS
-- ============================================================================

-- End customers belong to current producer
CREATE POLICY end_customer_isolation ON end_customers
    FOR ALL
    USING (producer_id = get_current_producer_id());

-- ============================================================================
-- POLICIES: MACHINE_MODELS
-- ============================================================================

CREATE POLICY machine_model_isolation ON machine_models
    FOR ALL
    USING (producer_id = get_current_producer_id());

-- ============================================================================
-- POLICIES: MACHINE_INSTANCES
-- ============================================================================

CREATE POLICY machine_instance_isolation ON machine_instances
    FOR ALL
    USING (producer_id = get_current_producer_id());

-- ============================================================================
-- POLICIES: DOCUMENTS
-- ============================================================================

CREATE POLICY document_isolation ON documents
    FOR ALL
    USING (producer_id = get_current_producer_id());

-- ============================================================================
-- POLICIES: DOCUMENT_CHUNKS
-- ============================================================================

-- Chunks inherit isolation from parent document
CREATE POLICY document_chunk_isolation ON document_chunks
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM documents
            WHERE documents.id = document_chunks.document_id
            AND documents.producer_id = get_current_producer_id()
        )
    );

-- ============================================================================
-- POLICIES: DOCUMENT_VERSIONS
-- ============================================================================

CREATE POLICY document_version_isolation ON document_versions
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM documents
            WHERE documents.id = document_versions.document_id
            AND documents.producer_id = get_current_producer_id()
        )
    );

-- ============================================================================
-- POLICIES: QUERIES
-- ============================================================================

CREATE POLICY query_isolation ON queries
    FOR ALL
    USING (producer_id = get_current_producer_id());

-- ============================================================================
-- POLICIES: USERS
-- ============================================================================

-- Users belong to end_customers which belong to producer
CREATE POLICY user_isolation ON users
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM end_customers
            WHERE end_customers.id = users.end_customer_id
            AND end_customers.producer_id = get_current_producer_id()
        )
    );

-- ============================================================================
-- POLICIES: USER_MACHINE_ACCESS
-- ============================================================================

-- Access records for users in current producer's end_customers
CREATE POLICY user_machine_access_isolation ON user_machine_access
    FOR ALL
    USING (
        EXISTS (
            SELECT 1 FROM users
            JOIN end_customers ON end_customers.id = users.end_customer_id
            WHERE users.id = user_machine_access.user_id
            AND end_customers.producer_id = get_current_producer_id()
        )
    );

-- ============================================================================
-- POLICIES: PRODUCER_ADMINS
-- ============================================================================

CREATE POLICY producer_admin_isolation ON producer_admins
    FOR ALL
    USING (producer_id = get_current_producer_id());

-- ============================================================================
-- BYPASS RLS FOR SUPERUSER (application service account)
-- ============================================================================

-- Grant BYPASSRLS to application database user
-- This allows application to SET producer_id context
-- IMPORTANT: Only application should have this privilege!

-- Example (adjust username as needed):
-- ALTER ROLE machinegpt_app BYPASSRLS;

-- ============================================================================
-- TESTING QUERIES
-- ============================================================================

-- Test isolation (run as application user):
/*

-- Set context for producer 1
SET app.current_producer_id = 1;

-- Should see only producer 1 data
SELECT * FROM producers;
SELECT * FROM end_customers;
SELECT * FROM documents;

-- Switch to producer 2
SET app.current_producer_id = 2;

-- Should see only producer 2 data
SELECT * FROM producers;
SELECT * FROM end_customers;
SELECT * FROM documents;

-- No context = no data (safe default)
RESET app.current_producer_id;
SELECT * FROM producers;  -- Empty result

*/

-- ============================================================================
-- MONITORING QUERIES
-- ============================================================================

-- Check which tables have RLS enabled:
/*
SELECT schemaname, tablename, rowsecurity 
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;
*/

-- Check RLS policies:
/*
SELECT schemaname, tablename, policyname, permissive, roles, cmd, qual
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
*/

-- ============================================================================
-- NOTES
-- ============================================================================

-- 1. RLS applies to ALL queries (SELECT, INSERT, UPDATE, DELETE)
-- 2. Superuser/BYPASSRLS role can see all data (application user)
-- 3. Regular users (if any) respect RLS policies
-- 4. Performance: RLS adds WHERE clause, ensure indexes on producer_id
-- 5. Testing: Use separate connections to test different tenants
-- 6. Session variables are connection-scoped, reset on new connection
