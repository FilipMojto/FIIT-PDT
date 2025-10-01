-- Users that posted tweets
INSERT INTO users (id, screen_name, name, description, verified, protected,
                   followers_count, friends_count, statuses_count, created_at, location, url)
SELECT DISTINCT
    (raw->'user'->>'id')::bigint,
    raw->'user'->>'screen_name',
    raw->'user'->>'name',
    raw->'user'->>'description',
    (raw->'user'->>'verified')::boolean,
    (raw->'user'->>'protected')::boolean,
    (raw->'user'->>'followers_count')::int,
    (raw->'user'->>'friends_count')::int,
    (raw->'user'->>'statuses_count')::int,
    (raw->'user'->>'created_at')::timestamp,
    raw->'user'->>'location',
    raw->'user'->>'url'
FROM raw_tweets
ON CONFLICT (id) DO NOTHING;

-- Users mentioned in tweets
INSERT INTO users (id, screen_name, name)
SELECT DISTINCT
    (elem->>'id')::bigint,
    elem->>'screen_name',
    elem->>'name'
FROM raw_tweets
CROSS JOIN LATERAL jsonb_array_elements(raw->'entities'->'user_mentions') AS elem
WHERE (elem->>'id') IS NOT NULL
ON CONFLICT (id) DO NOTHING;

-- Tweets
INSERT INTO tweets (id, created_at, full_text, lang, user_id, retweet_count, favorite_count, possibly_sensitive)
SELECT
    (raw->>'id')::bigint,
    (raw->>'created_at')::timestamp,
    COALESCE(raw->'extended_tweet'->>'full_text', raw->>'text'),
    raw->>'lang',
    (raw->'user'->>'id')::bigint,
    (raw->>'retweet_count')::int,
    (raw->>'favorite_count')::int,
    (raw->>'possibly_sensitive')::boolean
FROM raw_tweets
ON CONFLICT (id) DO NOTHING;

-- (1) zabezpeč UNIQUE index (ak ešte neexistuje)
CREATE UNIQUE INDEX IF NOT EXISTS hashtags_tag_idx ON hashtags (tag);

-- (2) vlož jedinečné tagy z raw_tweets
INSERT INTO hashtags (tag)
-- ->> extracts the value of of the text field as text
-- example: elem = {"text": "AI"}, then elem->>'text' = 'AI'
-- trim(...) removes leading/trailing whitespace
-- example: ' AI ' → 'AI'
-- lower(...) converts to lowercase
-- example: 'AI' → 'ai', This ensures 'AI' and 'ai' are treated as the same hashtag
-- Together: This ensures every hashtag is stored once, in clean lowercase form.
SELECT DISTINCT lower(trim(elem->> 'text'))
FROM raw_tweets
CROSS JOIN LATERAL jsonb_array_elements(raw->'entities'->'hashtags') AS elem
-- Makes sure the hashtags field is actually an array.
-- Some tweets might have null or other types.
WHERE jsonb_typeof(raw->'entities'->'hashtags') = 'array'
-- Some hashtag objects might be missing the text key.
-- Skip those.
  AND (elem->> 'text') IS NOT NULL
-- Skip empty or whitespace-only tags.
  AND trim(elem->> 'text') <> ''
-- Avoid violating the unique constraint by ignoring duplicates.
ON CONFLICT (tag) DO NOTHING;

-- (3) vlož do spojovacej tabuľky tweet_hashtag
INSERT INTO tweet_hashtag (tweet_id, hashtag_id)
SELECT
    (rt.raw->>'id')::bigint AS tweet_id,
    h.id AS hashtag_id
FROM raw_tweets rt
JOIN LATERAL jsonb_array_elements(rt.raw->'entities'->'hashtags') AS elem ON jsonb_typeof(rt.raw->'entities'->'hashtags') = 'array'
JOIN hashtags h ON lower(trim(elem->> 'text')) = h.tag
WHERE (elem->> 'text') IS NOT NULL
  AND trim(elem->> 'text') <> ''
ON CONFLICT (tweet_id, hashtag_id) DO NOTHING;

-- Places
INSERT INTO places (id, full_name, country, country_code, place_type)
SELECT DISTINCT
    raw->'place'->>'id' AS id,
    raw->'place'->>'full_name' AS full_name,
    raw->'place'->>'country' AS country,
    raw->'place'->>'country_code' AS country_code,
    raw->'place'->>'place_type' AS place_type
FROM raw_tweets
WHERE raw->'place' IS NOT NULL
  AND raw->'place'->>'id' IS NOT NULL
ON CONFLICT (id) DO NOTHING;

-- Update tweets with place_id
UPDATE tweets t
SET place_id = p.id
FROM raw_tweets rt
JOIN places p ON rt.raw->'place'->>'id' = p.id
WHERE t.id = (rt.raw->>'id')::bigint
  AND rt.raw->'place' IS NOT NULL
  AND rt.raw->'place'->>'id' IS NOT NULL;

-- Tweet URLs
INSERT INTO tweet_urls (tweet_id, url, expanded_url, display_url, unwound_url)
SELECT
    (rt.raw->>'id')::bigint AS tweet_id,
    elem->>'url' AS url,
    elem->>'expanded_url' AS expanded_url,
    elem->>'display_url' AS display_url,
    elem->>'unwound_url' AS unwound_url
FROM raw_tweets rt
CROSS JOIN LATERAL jsonb_array_elements(rt.raw->'entities'->'urls') AS elem
WHERE jsonb_typeof(rt.raw->'entities'->'urls') = 'array'
  AND (elem->>'url') IS NOT NULL
    AND trim(elem->>'url') <> ''
ON CONFLICT (tweet_id, url) DO NOTHING;

-- Tweet User Mentions
INSERT INTO tweet_user_mentions (tweet_id, mentioned_user_id, mentioned_screen_name, mentioned_name
)
SELECT
    (rt.raw->>'id')::bigint AS tweet_id,
    (elem->>'id')::bigint AS mentioned_user_id,
    elem->>'screen_name' AS mentioned_screen_name,
    elem->>'name' AS mentioned_name
FROM raw_tweets rt
CROSS JOIN LATERAL jsonb_array_elements(rt.raw->'entities'->'user_mentions') AS elem
WHERE jsonb_typeof(rt.raw->'entities'->'user_mentions') = 'array'
  AND (elem->>'id') IS NOT NULL
    AND trim(elem->>'id') <> ''
ON CONFLICT (tweet_id, mentioned_user_id) DO NOTHING;

-- Tweet Media
INSERT INTO tweet_media (tweet_id, media_id, type, media_url, media_url_https, display_url, expanded_url)
SELECT
    (rt.raw->>'id')::bigint AS tweet_id,
    (elem->>'id')::bigint AS media_id,
    elem->>'type' AS type,
    elem->>'media_url' AS media_url,
    elem->>'media_url_https' AS media_url_https,
    elem->>'display_url' AS display_url,
    elem->>'expanded_url' AS expanded_url
    -- elem->>'url' AS url,
    
    -- elem->'sizes' AS sizes
FROM raw_tweets rt
CROSS JOIN LATERAL jsonb_array_elements(rt.raw->'entities'->'media') AS elem
WHERE jsonb_typeof(rt.raw->'entities'->'media') = 'array'
  AND (elem->>'id') IS NOT NULL
    AND trim(elem->>'id') <> ''
ON CONFLICT (tweet_id, media_id) DO NOTHING;
-- Retweet relationships
UPDATE tweets t
SET retweeted_status_id = (rt.raw->'retweeted_status'->>'id')::bigint
FROM raw_tweets rt
WHERE t.id = (rt.raw->>'id')::bigint
  AND rt.raw->'retweeted_status' IS NOT NULL
  AND rt.raw->'retweeted_status'->>'id' IS NOT NULL;
-- Reply relationships
UPDATE tweets t
SET in_reply_to_status_id = (rt.raw->>'in_reply_to_status_id')::bigint
FROM raw_tweets rt
WHERE t.id = (rt.raw->>'id')::bigint
  AND rt.raw->>'in_reply_to_status_id' IS NOT NULL;
-- Quoted relationships
UPDATE tweets t
SET quoted_status_id = (rt.raw->>'quoted_status_id')::bigint
FROM raw_tweets rt
WHERE t.id = (rt.raw->>'id')::bigint
  AND rt.raw->>'quoted_status_id' IS NOT NULL;
-- Sources
UPDATE tweets t
SET source = regexp_replace(rt.raw->>'source', '<[^>]+>', '', 'g')
FROM raw_tweets rt
WHERE t.id = (rt.raw->>'id')::bigint
  AND rt.raw->>'source' IS NOT NULL;
-- Clean up raw_tweets table
DELETE FROM raw_tweets
WHERE id IN (SELECT id FROM tweets);
