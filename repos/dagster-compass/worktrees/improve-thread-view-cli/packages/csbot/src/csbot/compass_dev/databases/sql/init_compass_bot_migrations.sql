-- Migration user with elevated privileges
DO
$$
BEGIN
    IF NOT EXISTS (SELECT * FROM pg_user WHERE usename = 'compassbot_migrations') THEN
        CREATE USER compassbot_migrations;
    END IF;
END
$$;

-- allow IAM auth
GRANT rds_iam TO compassbot;

-- Grant schema-level permissions to migrations user
GRANT ALL PRIVILEGES ON SCHEMA public TO compassbot_migrations;

-- Grant full DDL permissions on existing objects
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO compassbot_migrations;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO compassbot_migrations;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO compassbot_migrations;

-- Grant full DDL permissions on future objects
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL PRIVILEGES ON TABLES TO compassbot_migrations;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL PRIVILEGES ON SEQUENCES TO compassbot_migrations;
ALTER DEFAULT PRIVILEGES IN SCHEMA public 
    GRANT ALL PRIVILEGES ON FUNCTIONS TO compassbot_migrations;
