-- datadog setup
DO
$$
BEGIN
    IF NOT EXISTS (SELECT * FROM pg_user WHERE usename = 'datadog') THEN
        CREATE USER datadog WITH CONNECTION LIMIT 5;
    END IF;
END
$$
;

-- allow IAM auth
GRANT rds_iam TO compassbot;

ALTER ROLE datadog INHERIT;

CREATE SCHEMA IF NOT EXISTS datadog;
GRANT USAGE ON SCHEMA datadog TO datadog;
GRANT USAGE ON SCHEMA public TO datadog;
GRANT pg_monitor TO datadog;
CREATE EXTENSION IF NOT EXISTS pg_stat_statements schema public;
GRANT SELECT ON pg_stat_database TO datadog;

CREATE OR REPLACE FUNCTION datadog.explain_statement(
   l_query TEXT,
   OUT explain JSON
)
RETURNS SETOF JSON AS
$$
DECLARE
curs REFCURSOR;
plan JSON;

BEGIN
   OPEN curs FOR EXECUTE pg_catalog.concat('EXPLAIN (FORMAT JSON) ', l_query);
   FETCH curs INTO plan;
   CLOSE curs;
   RETURN QUERY SELECT plan;
END;
$$
LANGUAGE 'plpgsql'
RETURNS NULL ON NULL INPUT
SECURITY DEFINER;
