
CREATE UNLOGGED TABLE users (
    id bigint PRIMARY KEY,
    screen_name TEXT,
    name TEXT,
    description TEXT,
    verified BOOLEAN,
    protected BOOLEAN,
    followers_count INT,
    friends_count INT,
    statuses_count INT,
    created_at TIMESTAMP,
    location TEXT,
    url TEXT
);

CREATE UNLOGGED TABLE places (
    id TEXT PRIMARY KEY,
    full_name TEXT,
    country TEXT,
    country_code TEXT,
    place_type TEXT
);

-- TWEETS table
CREATE UNLOGGED TABLE tweets (
    id BIGINT PRIMARY KEY,
    created_at TIMESTAMP,
    full_text TEXT,
    display_from INT,
    display_to INT,
    lang TEXT,
    user_id BIGINT NULL REFERENCES users(id) ON DELETE SET NULL, -- nullable FK
    source TEXT,
    in_reply_to_status_id BIGINT,   -- soft reference, no FK
    quoted_status_id BIGINT,        -- soft reference, no FK
    retweeted_status_id BIGINT,     -- soft reference, no FK
    place_id TEXT REFERENCES places(id),
    retweet_count INT,
    favorite_count INT,
    possibly_sensitive BOOLEAN
);

-- HASHTAGS table
CREATE UNLOGGED TABLE hashtags (
    id bigint PRIMARY KEY,
    tag TEXT UNIQUE
);

-- TWEET_HASHTAG table
CREATE UNLOGGED TABLE tweet_hashtag (
    tweet_id BIGINT REFERENCES tweets(id) ON DELETE CASCADE,
    hashtag_id BIGINT REFERENCES hashtags(id) ON DELETE CASCADE,
    PRIMARY KEY(tweet_id, hashtag_id)
);

-- TWEET_URLS table
CREATE UNLOGGED TABLE tweet_urls (
    tweet_id BIGINT REFERENCES tweets(id) ON DELETE CASCADE,
    url TEXT,
    expanded_url TEXT,
    display_url TEXT,
    unwound_url TEXT,
    PRIMARY KEY(tweet_id, url)
);

-- TWEET_USER_MENTIONS table
CREATE UNLOGGED TABLE tweet_user_mentions (
    tweet_id BIGINT REFERENCES tweets(id) ON DELETE CASCADE,
    mentioned_user_id BIGINT REFERENCES users(id) ON DELETE CASCADE,
    mentioned_screen_name TEXT,
    mentioned_name TEXT,
    PRIMARY KEY(tweet_id, mentioned_user_id)
);

-- TWEET_MEDIA table
CREATE UNLOGGED TABLE tweet_media (
    tweet_id BIGINT REFERENCES tweets(id) ON DELETE CASCADE,
    media_id BIGINT,
    type TEXT,
    media_url TEXT,
    media_url_https TEXT,
    display_url TEXT,
    expanded_url TEXT,
    PRIMARY KEY(tweet_id, media_id)
);
