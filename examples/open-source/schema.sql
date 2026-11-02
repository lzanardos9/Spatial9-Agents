-- One row per track and version. The worker and the webhook are the only writers.
CREATE TABLE IF NOT EXISTS tracks (
  track_id     text NOT NULL,
  version      int  NOT NULL DEFAULT 1,
  object_key   text NOT NULL,                       -- path in the masters bucket
  status       text NOT NULL DEFAULT 'pending'
               CHECK (status IN ('pending', 'rejected', 'submitted', 'working', 'completed', 'failed', 'canceled')),
  task_id      text,                                -- Spatial9 A2A task id
  loudness_lufs numeric,                            -- integrated loudness measured by FFmpeg
  outputs      jsonb NOT NULL DEFAULT '[]',         -- [{name, key}] saved in the immersive bucket
  error        text NOT NULL DEFAULT '',
  updated_at   timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (track_id, version)
);

CREATE UNIQUE INDEX IF NOT EXISTS tracks_task_id ON tracks (task_id) WHERE task_id IS NOT NULL;

-- Append-only audit trail: every state change, from any source.
CREATE TABLE IF NOT EXISTS track_events (
  id        bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
  track_id  text NOT NULL,
  version   int  NOT NULL,
  event     text NOT NULL,
  detail    text NOT NULL DEFAULT '',
  at        timestamptz NOT NULL DEFAULT now()
);
