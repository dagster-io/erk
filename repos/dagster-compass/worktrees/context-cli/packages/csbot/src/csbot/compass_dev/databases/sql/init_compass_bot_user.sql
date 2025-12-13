-- Compass bot user initialization
DO
$$
BEGIN
    IF NOT EXISTS (SELECT * FROM pg_user WHERE usename = 'compassbot') THEN
        CREATE USER compassbot;
    END IF;
END
$$
;

-- allow IAM auth
GRANT rds_iam TO compassbot;

--- Grant on all existing objects
GRANT USAGE ON SCHEMA public TO compassbot;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO compassbot;
GRANT SELECT, UPDATE ON ALL SEQUENCES IN SCHEMA public TO compassbot;
--- Grant on all future objects
ALTER DEFAULT PRIVILEGES
    GRANT USAGE ON SCHEMAS TO compassbot;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO compassbot;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT SELECT, UPDATE ON SEQUENCES TO compassbot;
