-- Read interfaces of the system of record (ADR 0009). Run as the owner schema.

-- Current value of every period: the open revisions.
CREATE OR REPLACE VIEW observation_current AS
SELECT series_key, ref_date, value, known_from, file_id
FROM observation_revision
WHERE known_to IS NULL
/
-- "What was known on a given date": every period as it stood at p_as_of (UTC).
-- Usage: SELECT * FROM {p}_OWNER.observation_as_of(TIMESTAMP '2026-11-01 00:00:00')
CREATE OR REPLACE FUNCTION observation_as_of(p_as_of TIMESTAMP)
    RETURN VARCHAR2 SQL_MACRO(TABLE)
IS
BEGIN
    RETURN q'[
        SELECT series_key, ref_date, value, known_from, known_to
        FROM {p}_OWNER.observation_revision
        WHERE known_from <= p_as_of
          AND (known_to IS NULL OR known_to > p_as_of)
    ]';
END;
/
-- Fill DATA_DICTIONARY from Oracle's own catalog: the description (comment) and classification
-- (annotation) of every column of every permanent table. Setup runs it after every change, so the
-- dictionary cannot drift from the schema. (A view over the catalog cannot be granted to the read
-- role: Oracle does not allow re-granting its catalog views.)
CREATE OR REPLACE PROCEDURE refresh_data_dictionary AUTHID DEFINER IS
BEGIN
    DELETE FROM data_dictionary;
    INSERT INTO data_dictionary (
        table_name, table_description, table_classification, column_id, column_name, data_type,
        nullable, column_description, column_classification, refreshed_at)
    SELECT
        c.table_name, tc.comments, ta.annotation_value, c.column_id, c.column_name, c.data_type,
        c.nullable, cc.comments, ca.annotation_value, SYS_EXTRACT_UTC(SYSTIMESTAMP)
    FROM user_tab_columns c
    JOIN user_tables t
      ON t.table_name = c.table_name AND t.temporary = 'N'
    LEFT JOIN user_tab_comments tc
      ON tc.table_name = c.table_name
    LEFT JOIN user_col_comments cc
      ON cc.table_name = c.table_name AND cc.column_name = c.column_name
    LEFT JOIN user_annotations_usage ta
      ON ta.object_name = c.table_name AND ta.object_type = 'TABLE'
     AND ta.column_name IS NULL AND ta.annotation_name = 'CLASSIFICATION'
    LEFT JOIN user_annotations_usage ca
      ON ca.object_name = c.table_name AND ca.object_type = 'TABLE'
     AND ca.column_name = c.column_name AND ca.annotation_name = 'CLASSIFICATION'
    WHERE c.column_name NOT LIKE 'SYS\_%' ESCAPE '\';
    COMMIT;
END;
/
COMMENT ON TABLE observation_current IS 'Current value of every period (open revisions only).'
/
