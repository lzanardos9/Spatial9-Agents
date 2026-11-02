-- Databricks notebook source
-- MAGIC %md
-- MAGIC # 06 Gold: catalog coverage, throughput and failure reasons
-- MAGIC Point an AI/BI dashboard or Genie space at these views. Set the catalog and schema widgets first.

-- COMMAND ----------

CREATE WIDGET TEXT catalog DEFAULT 'main';
CREATE WIDGET TEXT schema DEFAULT 'spatial9_accelerator';
USE CATALOG IDENTIFIER(:catalog);
USE SCHEMA IDENTIFIER(:schema);

-- COMMAND ----------

-- How much of the catalog is immersive already, per route.
CREATE OR REPLACE VIEW gold_catalog_coverage AS
SELECT route, skill,
       count(*)                                             AS tracks,
       count_if(status = 'completed')                       AS completed,
       count_if(status = 'running')                         AS running,
       count_if(status = 'pending')                         AS waiting,
       count_if(status = 'failed')                          AS failed,
       round(100 * count_if(status = 'completed') / count(*), 1) AS pct_done
FROM render_queue
GROUP BY route, skill;

-- COMMAND ----------

-- Renders per day against the 20-per-day limit, and median time from start to finish.
CREATE OR REPLACE VIEW gold_daily_throughput AS
WITH spans AS (
  SELECT track_id, version, route,
         min(CASE WHEN event = 'started' THEN at END)   AS started_at,
         max(CASE WHEN event = 'completed' THEN at END) AS completed_at
  FROM render_events GROUP BY track_id, version, route
)
SELECT date(started_at) AS day, route,
       count(*) AS started,
       count(completed_at) AS completed,
       percentile_approx(timestampdiff(MINUTE, started_at, completed_at), 0.5) AS median_minutes,
       20 - count(*) AS remaining_daily_capacity
FROM spans WHERE started_at IS NOT NULL
GROUP BY ALL;

-- COMMAND ----------

-- The plain-language reasons Spatial9 gave for failures, most common first.
CREATE OR REPLACE VIEW gold_failure_reasons AS
SELECT route, coalesce(nullif(error, ''), 'unknown') AS reason, count(*) AS tracks, max(updated_at) AS last_seen
FROM render_queue WHERE status = 'failed' OR (error IS NOT NULL AND error <> '')
GROUP BY ALL ORDER BY tracks DESC;

-- COMMAND ----------

SELECT * FROM gold_catalog_coverage;
