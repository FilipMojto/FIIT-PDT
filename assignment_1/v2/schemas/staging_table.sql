-- -- staging raw JSON lines
-- CREATE TABLE IF NOT EXISTS staging_raw (
--   file_name text NOT NULL,
--   line_no   bigint NOT NULL,
--   raw       jsonb NOT NULL,
--   inserted_at timestamptz DEFAULT now()
-- );

-- CREATE TABLE IF NOT EXISTS staging_raw_text (
--   file_name text NOT NULL,
--   line_no   bigint NOT NULL,
--   raw       text NOT NULL,
--   inserted_at timestamptz DEFAULT now()
-- );

-- -- index pre rýchle vyhľadávanie podľa tweet id v raw (ak extrahuješ id často)
-- CREATE INDEX IF NOT EXISTS idx_staging_raw_tweetid ON staging_raw ((raw->>'id'));

-- -- tabulka pre zaznamenanie behov importu (protokol)
-- CREATE TABLE IF NOT EXISTS import_runs (
--   id serial PRIMARY KEY,
--   started_at timestamptz NOT NULL DEFAULT now(),
--   finished_at timestamptz,
--   files_processed int,
--   rows_read bigint,
--   rows_staging bigint,
--   notes text
-- );

-- CREATE UNLOGGED TABLE IF NOT EXISTS tweets_staging (
--   id bigint PRIMARY KEY,
--   created_at timestamptz,
--   full_text text,
--   display_from int,
--   display_to int,
--   lang text,
--   user_id bigint, -- môže byť NULL
--   source text,
--   in_reply_to_status_id bigint,
--   quoted_status_id bigint,
--   retweeted_status_id bigint,
--   place_id text,
--   retweet_count int,
--   favorite_count int,
--   possibly_sensitive boolean
-- );

-- CREATE UNLOGGED TABLE IF NOT EXISTS users_staging (
--   id bigint PRIMARY KEY,
--   screen_name text,
--   name text,
--   description text,
--   verified boolean,
--   protected boolean,
--   followers_count int,
--   friends_count int,
--   statuses_count int,
--   created_at timestamptz,
--   location text,
--   url text
-- );

-- CREATE UNLOGGED TABLE IF NOT EXISTS places_staging (
--   id text PRIMARY KEY,
--   full_name text,
--   country text,
--   country_code text,
--   place_type text
-- );

-- CREATE UNLOGGED TABLE IF NOT EXISTS hashtags_staging (
--   id bigint PRIMARY KEY, -- generated hash id
--   tag text UNIQUE
-- );

-- CREATE UNLOGGED TABLE IF NOT EXISTS tweet_hashtag_staging (
--   tweet_id bigint NOT NULL,
--   hashtag_id bigint NOT NULL,
--   PRIMARY KEY (tweet_id, hashtag_id)
-- );

-- CREATE UNLOGGED TABLE IF NOT EXISTS tweet_urls_staging (
--   tweet_id bigint NOT NULL,
--   url text NOT NULL,
--   expanded_url text,
--   display_url text,
--   unwound_url text,
--   PRIMARY KEY (tweet_id, url)
-- );

-- CREATE UNLOGGED TABLE IF NOT EXISTS tweet_user_mentions_staging (
--   tweet_id bigint NOT NULL,
--   mentioned_user_id bigint NOT NULL,
--   mentioned_screen_name text,
--   mentioned_name text,
--   PRIMARY KEY (tweet_id, mentioned_user_id)
-- );

-- CREATE UNLOGGED TABLE IF NOT EXISTS tweet_media_staging (
--   tweet_id bigint NOT NULL,
--   media_id bigint NOT NULL,
--   type text,
--   media_url text,
--   media_url_https text,
--   display_url text,
--   expanded_url text,
--   PRIMARY KEY (tweet_id, media_id)
-- );


CREATE UNLOGGED TABLE IF NOT EXISTS tweets_staging (LIKE tweets INCLUDING DEFAULTS EXCLUDING CONSTRAINTS);

CREATE UNLOGGED TABLE IF NOT EXISTS users_staging (LIKE users INCLUDING DEFAULTS EXCLUDING CONSTRAINTS);

CREATE UNLOGGED TABLE IF NOT EXISTS places_staging  (LIKE places INCLUDING DEFAULTS EXCLUDING CONSTRAINTS);

CREATE UNLOGGED TABLE IF NOT EXISTS hashtags_staging  (LIKE hashtags INCLUDING DEFAULTS EXCLUDING CONSTRAINTS);

CREATE UNLOGGED TABLE IF NOT EXISTS tweet_hashtag_staging  (LIKE tweet_hashtag INCLUDING DEFAULTS EXCLUDING CONSTRAINTS);

CREATE UNLOGGED TABLE IF NOT EXISTS tweet_urls_staging (LIKE tweet_urls INCLUDING DEFAULTS EXCLUDING CONSTRAINTS);

CREATE UNLOGGED TABLE IF NOT EXISTS tweet_user_mentions_staging (LIKE tweet_user_mentions INCLUDING DEFAULTS EXCLUDING CONSTRAINTS);

CREATE UNLOGGED TABLE IF NOT EXISTS tweet_media_staging (LIKE tweet_media INCLUDING DEFAULTS EXCLUDING CONSTRAINTS);