# Databricks notebook source
# MAGIC %md
# MAGIC # 02 Ingest: new masters become queue rows
# MAGIC Auto Loader watches the masters Volume. Each new file is recorded once (bronze) and added to the
# MAGIC render queue as a pending MCP render. Change `route` and `skill` per row to use A2A or the REST API.

# COMMAND ----------

# MAGIC %run ./00_config

# COMMAND ----------

from pyspark.sql import functions as F

masters = (
    spark.readStream.format("cloudFiles")  # noqa: F821
    .option("cloudFiles.format", "binaryFile")
    .option("pathGlobFilter", "*.{wav,flac,aif,aiff}")
    .load(MASTERS)
    .drop("content")                                   # metadata only: Spatial9 reads the file through an upload link
    .withColumn("path", F.regexp_replace("path", "^dbfs:", ""))
    .withColumn("track_id", F.regexp_extract("path", r"([^/]+)\.[^./]+$", 1))
    .withColumn("ingested_at", F.current_timestamp())
)

(
    masters.writeStream
    .option("checkpointLocation", f"{CHECKPOINTS}/masters")
    .trigger(availableNow=True)                        # process what is new, then stop: cheap on a schedule
    .toTable(f"{NS}.bronze_masters")
    .awaitTermination()
)

# COMMAND ----------

# Version 1 of every new track becomes a pending immersive render. Re-running this cell never duplicates rows.
spark.sql(f"""
MERGE INTO {QUEUE} q
USING (SELECT track_id, max(path) AS path FROM {NS}.bronze_masters GROUP BY track_id) m
ON q.track_id = m.track_id AND q.version = 1 AND q.route = 'mcp'
WHEN NOT MATCHED THEN INSERT (track_id, version, route, skill, title, source_path, style, status, updated_at)
VALUES (m.track_id, 1, 'mcp', 'spatial_audio', initcap(replace(replace(m.track_id, '_', ' '), '-', ' ')),
        m.path, 'live_concert', 'pending', current_timestamp())
""")

display(spark.table(QUEUE).groupBy("route", "status").count())  # noqa: F821
