CREATE TABLE IF NOT EXISTS raw_tweets (
    id BIGINT PRIMARY KEY,
    raw JSONB NOT NULL
);

-- 1) staging pre base64
CREATE UNLOGGED TABLE IF NOT EXISTS raw_base64 (
  id bigint PRIMARY KEY,
  payload text NOT NULL
);

-- 2) log chýb - aké payloady zlyhali pri dekódovaní alebo parse
CREATE TABLE IF NOT EXISTS failed_base64 (
  id bigint,
  payload text,
  err text,
  created_at timestamptz DEFAULT now()
);

-- 3) bezpečná importná funkcia - spracuje všetko v raw_base64
CREATE OR REPLACE FUNCTION import_raw_base64()
RETURNS void LANGUAGE plpgsql AS $$
DECLARE
  r record;
  v text;
BEGIN
  FOR r IN SELECT id, payload FROM raw_base64 LOOP
    BEGIN
      -- dekódovať a konvertovať na text
      v := convert_from(decode(r.payload, 'base64'), 'UTF8');
      -- pokúsime sa vložiť ako jsonb
      INSERT INTO raw_tweets (id, raw)
      VALUES (r.id, v::jsonb)
      ON CONFLICT (id) DO NOTHING;
    EXCEPTION WHEN others THEN
      -- ak sa niečo pokazí (dekódovanie, invalid json), logneme to
      INSERT INTO failed_base64 (id, payload, err) VALUES (r.id, r.payload, SQLERRM);
    END;
  END LOOP;
END;
$$;