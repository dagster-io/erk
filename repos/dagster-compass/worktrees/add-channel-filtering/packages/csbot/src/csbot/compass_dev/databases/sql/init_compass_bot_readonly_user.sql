-- Compass bot readonly user initialization
DO
$$
BEGIN
    IF NOT EXISTS (SELECT * FROM pg_user WHERE usename = 'compassbot_readonly') THEN
        CREATE USER compassbot_readonly;
    END IF;
END
$$
;

-- allow IAM auth
GRANT rds_iam TO compassbot;

--- Grant on all existing objects
GRANT USAGE ON SCHEMA public TO compassbot_readonly;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO compassbot_readonly;
GRANT SELECT ON ALL SEQUENCES IN SCHEMA public TO compassbot_readonly;
--- Grant on all future objects
ALTER DEFAULT PRIVILEGES
    GRANT USAGE ON SCHEMAS TO compassbot_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON TABLES TO compassbot_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public
    GRANT SELECT ON SEQUENCES TO compassbot_readonly;
