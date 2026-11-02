-- Spatial9 on Snowflake: one-time setup. Run as a role that can create integrations (ACCOUNTADMIN or delegated).
USE ROLE ACCOUNTADMIN;
CREATE DATABASE IF NOT EXISTS MEDIA;
CREATE SCHEMA IF NOT EXISTS MEDIA.SPATIAL;
USE SCHEMA MEDIA.SPATIAL;

-- 1. Allow outbound calls only to spatial9.ai.
CREATE OR REPLACE NETWORK RULE spatial9_egress
  MODE = EGRESS
  TYPE = HOST_PORT
  VALUE_LIST = ('spatial9.ai');

-- Download links come from Spatial9's file storage. Add the host returned by get_downloads
-- to a second rule if you copy files into a stage (check one real link first).

-- 2. The key lives in a secret, never in code.
CREATE OR REPLACE SECRET spatial9_key
  TYPE = GENERIC_STRING
  SECRET_STRING = 's9_replace_me';

-- 3. Tie the rule and the secret together.
CREATE OR REPLACE EXTERNAL ACCESS INTEGRATION spatial9_access
  ALLOWED_NETWORK_RULES = (spatial9_egress)
  ALLOWED_AUTHENTICATION_SECRETS = (spatial9_key)
  ENABLED = TRUE;

GRANT USAGE ON INTEGRATION spatial9_access TO ROLE CATALOG_ENGINEER;
GRANT READ ON SECRET spatial9_key TO ROLE CATALOG_ENGINEER;

-- 4. Work queue and stage for finished files.
CREATE TABLE IF NOT EXISTS RENDERS_QUEUE (
  TRACK_ID    STRING NOT NULL,
  VERSION     NUMBER DEFAULT 1,
  TITLE       STRING NOT NULL,
  SOURCE_URL  STRING,                   -- presigned https link to the master
  STYLE       STRING DEFAULT 'live_concert',
  STATUS      STRING DEFAULT 'pending',
  JOB_ID      STRING,
  STAGE       STRING,
  DOWNLOADS   VARIANT,
  ERROR       STRING,
  UPDATED_AT  TIMESTAMP_TZ
);
CREATE STAGE IF NOT EXISTS IMMERSIVE ENCRYPTION = (TYPE = 'SNOWFLAKE_SSE');
