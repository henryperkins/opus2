-- Add missing columns to projects table
ALTER TABLE projects ADD COLUMN color VARCHAR(7) DEFAULT '#3B82F6';
ALTER TABLE projects ADD COLUMN emoji VARCHAR(10) DEFAULT '📁';
ALTER TABLE projects ADD COLUMN tags JSON DEFAULT '[]';
