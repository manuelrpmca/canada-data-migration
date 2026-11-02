-- Accounts and roles for the governed system of record (ADR 0009).
-- CREATE SEQUENCE is needed for the identity columns.
-- Run as SYSTEM in the FREEPDB1 pluggable database by `uv run cdm oracle setup`.
--
-- Placeholders, replaced by cdm before running: {p} = account prefix (CDM, or CDMTEST in the
-- integration tests), {loader_password}, {migration_password}.
-- Statements are separated by a line holding only "/", so the file also runs in SQL*Plus.
--
-- Separation of duties:
--   {p}_OWNER      owns every table, view and the load package. Schema-only account
--                  (NO AUTHENTICATION): nobody can sign in as it; DDL reaches it only through a
--                  proxy connection from SYSTEM.
--   {p}_LOADER     can only run the load package ({p}_LOAD_ROLE). No direct table access.
--   {p}_MIGRATION  read-only ({p}_READ_ROLE): what the migration in M5 connects as.

CREATE USER IF NOT EXISTS {p}_OWNER NO AUTHENTICATION
    DEFAULT TABLESPACE users QUOTA 500M ON users
/
GRANT CREATE SESSION, CREATE TABLE, CREATE VIEW, CREATE PROCEDURE, CREATE SEQUENCE TO {p}_OWNER
/
ALTER USER {p}_OWNER GRANT CONNECT THROUGH SYSTEM
/
CREATE ROLE IF NOT EXISTS {p}_LOAD_ROLE
/
CREATE ROLE IF NOT EXISTS {p}_READ_ROLE
/
CREATE USER IF NOT EXISTS {p}_LOADER IDENTIFIED BY "{loader_password}"
/
ALTER USER {p}_LOADER IDENTIFIED BY "{loader_password}"
/
GRANT CREATE SESSION, {p}_LOAD_ROLE TO {p}_LOADER
/
CREATE USER IF NOT EXISTS {p}_MIGRATION IDENTIFIED BY "{migration_password}"
/
ALTER USER {p}_MIGRATION IDENTIFIED BY "{migration_password}"
/
GRANT CREATE SESSION, {p}_READ_ROLE TO {p}_MIGRATION
/
