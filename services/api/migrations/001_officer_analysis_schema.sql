-- Migration: Create Officer Analysis Tables
-- Date: May 27, 2026
-- Purpose: Support 4-step officer analysis form workflow

-- Table 1: Officer Analyses
CREATE TABLE IF NOT EXISTS officer_analyses (
  analysis_id TEXT PRIMARY KEY,
  referral_id TEXT NOT NULL,
  officer_id TEXT NOT NULL,
  officer_name TEXT,
  badge_number TEXT,
  district TEXT,
  step1 JSON NOT NULL,
  step2 JSON NOT NULL,
  step3 JSON NOT NULL,
  step4 JSON NOT NULL,
  submitted_at TIMESTAMP NOT NULL,
  signed_at TIMESTAMP,
  FOREIGN KEY (referral_id) REFERENCES referral_packages(referral_id)
);

-- Create index on referral_id for quick lookups
CREATE INDEX IF NOT EXISTS idx_officer_analyses_referral_id
ON officer_analyses(referral_id);

-- Create index on officer_id for audit queries
CREATE INDEX IF NOT EXISTS idx_officer_analyses_officer_id
ON officer_analyses(officer_id);

-- Table 2: Audit Log
CREATE TABLE IF NOT EXISTS audit_log (
  log_id TEXT PRIMARY KEY,
  officer_id TEXT,
  action TEXT,
  referral_id TEXT,
  analysis_id TEXT,
  timestamp TIMESTAMP,
  details JSON
);

-- Create index on timestamp for chronological queries
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp
ON audit_log(timestamp DESC);

-- Create index on officer_id for officer activity tracking
CREATE INDEX IF NOT EXISTS idx_audit_log_officer_id
ON audit_log(officer_id);

-- Alter referral_packages table to link analyses
ALTER TABLE referral_packages ADD COLUMN IF NOT EXISTS (
  edited_sections JSON,
  analysis_id TEXT,
  final_package_status TEXT DEFAULT 'draft',
  pdf_export_ready BOOLEAN DEFAULT 0
);

-- Create index on analysis_id
CREATE INDEX IF NOT EXISTS idx_referral_packages_analysis_id
ON referral_packages(analysis_id);

-- Verify migration success
SELECT 'Officer Analysis Schema' as migration,
       'SUCCESS' as status,
       count(*) as tables_created
FROM sqlite_master
WHERE type='table'
AND name IN ('officer_analyses', 'audit_log');
