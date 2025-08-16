-- PostgreSQL Development Database Initialization
-- Create development database and user
CREATE DATABASE harbor_dev_test;
GRANT ALL PRIVILEGES ON DATABASE harbor_dev TO harbor_dev;
GRANT ALL PRIVILEGES ON DATABASE harbor_dev_test TO harbor_dev;

-- Create extensions if needed
\c harbor_dev;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

\c harbor_dev_test;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
