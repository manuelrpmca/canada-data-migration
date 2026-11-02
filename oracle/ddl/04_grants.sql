-- Least-privilege grants (ADR 0009). Run as the owner schema, which grants on its own objects.
-- The loader role can only run the load package; the read role can only read.

GRANT EXECUTE ON cdm_load TO {p}_LOAD_ROLE
/
GRANT SELECT ON source_system TO {p}_READ_ROLE
/
GRANT SELECT ON series TO {p}_READ_ROLE
/
GRANT SELECT ON landed_file TO {p}_READ_ROLE
/
GRANT SELECT ON observation_revision TO {p}_READ_ROLE
/
GRANT SELECT ON load_audit TO {p}_READ_ROLE
/
GRANT SELECT ON observation_current TO {p}_READ_ROLE
/
GRANT SELECT ON data_dictionary TO {p}_READ_ROLE
/
GRANT EXECUTE ON observation_as_of TO {p}_READ_ROLE
/
-- Last step of setup: read the catalog into the data dictionary.
BEGIN
    refresh_data_dictionary;
END;
/
