-- Tables of the governed system of record (ADR 0009). Run as the owner schema through a proxy
-- connection, so every object below belongs to {p}_OWNER.
--
-- Data dictionary: every table and column carries a COMMENT (its description) and a
-- `classification` annotation (Oracle 23ai annotations). DATA_DICTIONARY copies both from
-- Oracle's own catalog on every setup (03_views.sql), so the dictionary cannot drift from the schema.
-- Classification levels used here:
--   Public    published open data and its reference metadata (Statistics Canada, Bank of Canada)
--   Internal  operational metadata about loads (run ids, hashes, database users)
-- The project holds no personal or confidential data; the levels exist to show the mechanism.
--
-- CREATE TABLE IF NOT EXISTS keeps setup re-runnable without touching data. To change a table
-- definition locally, delete the container's data with `uv run cdm oracle down --delete-data`.

CREATE TABLE IF NOT EXISTS source_system (
    source_code   VARCHAR2(20)   NOT NULL ANNOTATIONS (classification 'Public'),
    name          VARCHAR2(100)  NOT NULL ANNOTATIONS (classification 'Public'),
    terms_url     VARCHAR2(200)  NOT NULL ANNOTATIONS (classification 'Public'),
    CONSTRAINT source_system_pk PRIMARY KEY (source_code)
) ANNOTATIONS (classification 'Public')
/
CREATE TABLE IF NOT EXISTS series (
    series_key    VARCHAR2(50)   NOT NULL ANNOTATIONS (classification 'Public'),
    source_code   VARCHAR2(20)   NOT NULL ANNOTATIONS (classification 'Public'),
    series_id     VARCHAR2(50)   NOT NULL ANNOTATIONS (classification 'Public'),
    product_id    NUMBER(12)              ANNOTATIONS (classification 'Public'),
    name          VARCHAR2(200)  NOT NULL ANNOTATIONS (classification 'Public'),
    unit          VARCHAR2(50)   NOT NULL ANNOTATIONS (classification 'Public'),
    frequency     VARCHAR2(10)   NOT NULL ANNOTATIONS (classification 'Public'),
    start_date    DATE           NOT NULL ANNOTATIONS (classification 'Public'),
    updated_at    TIMESTAMP      NOT NULL ANNOTATIONS (classification 'Internal'),
    CONSTRAINT series_pk PRIMARY KEY (series_key),
    CONSTRAINT series_source_fk FOREIGN KEY (source_code) REFERENCES source_system (source_code),
    CONSTRAINT series_frequency_ck CHECK (frequency IN ('daily', 'monthly'))
) ANNOTATIONS (classification 'Public')
/
CREATE TABLE IF NOT EXISTS landed_file (
    file_id       NUMBER GENERATED ALWAYS AS IDENTITY ANNOTATIONS (classification 'Internal'),
    series_key    VARCHAR2(50)   NOT NULL ANNOTATIONS (classification 'Public'),
    run_id        VARCHAR2(40)   NOT NULL ANNOTATIONS (classification 'Internal'),
    received_at   TIMESTAMP      NOT NULL ANNOTATIONS (classification 'Internal'),
    sha256        CHAR(64)       NOT NULL ANNOTATIONS (classification 'Internal'),
    payload       CLOB           NOT NULL ANNOTATIONS (classification 'Public'),
    loaded_at     TIMESTAMP      NOT NULL ANNOTATIONS (classification 'Internal'),
    loaded_by     VARCHAR2(128)  NOT NULL ANNOTATIONS (classification 'Internal'),
    CONSTRAINT landed_file_pk PRIMARY KEY (file_id),
    CONSTRAINT landed_file_uk UNIQUE (series_key, run_id),
    CONSTRAINT landed_file_series_fk FOREIGN KEY (series_key) REFERENCES series (series_key),
    CONSTRAINT landed_file_payload_json_ck CHECK (payload IS JSON)
) ANNOTATIONS (classification 'Public')
/
-- Effective-dated revision history. One row per value the source published for a period:
-- known_from is when this project first received it, known_to when a different value replaced it
-- (NULL while it is still the current value). Rows are never updated except to close them.
CREATE TABLE IF NOT EXISTS observation_revision (
    series_key    VARCHAR2(50)   NOT NULL ANNOTATIONS (classification 'Public'),
    ref_date      DATE           NOT NULL ANNOTATIONS (classification 'Public'),
    value         NUMBER         NOT NULL ANNOTATIONS (classification 'Public'),
    known_from    TIMESTAMP      NOT NULL ANNOTATIONS (classification 'Public'),
    known_to      TIMESTAMP               ANNOTATIONS (classification 'Public'),
    file_id       NUMBER         NOT NULL ANNOTATIONS (classification 'Internal'),
    closed_by_file_id NUMBER              ANNOTATIONS (classification 'Internal'),
    CONSTRAINT observation_revision_pk PRIMARY KEY (series_key, ref_date, known_from),
    CONSTRAINT observation_revision_series_fk FOREIGN KEY (series_key)
        REFERENCES series (series_key),
    CONSTRAINT observation_revision_file_fk FOREIGN KEY (file_id) REFERENCES landed_file (file_id),
    CONSTRAINT observation_revision_closed_fk FOREIGN KEY (closed_by_file_id)
        REFERENCES landed_file (file_id),
    CONSTRAINT observation_revision_window_ck CHECK (known_to IS NULL OR known_to > known_from),
    CONSTRAINT observation_revision_closed_ck
        CHECK ((known_to IS NULL) = (closed_by_file_id IS NULL))
) ANNOTATIONS (classification 'Public')
/
-- At most one current value per series and period: the index holds only open rows.
CREATE UNIQUE INDEX IF NOT EXISTS observation_current_uk ON observation_revision (
    CASE WHEN known_to IS NULL THEN series_key END,
    CASE WHEN known_to IS NULL THEN ref_date END
)
/
CREATE TABLE IF NOT EXISTS load_audit (
    load_id       NUMBER GENERATED ALWAYS AS IDENTITY ANNOTATIONS (classification 'Internal'),
    series_key    VARCHAR2(50)   NOT NULL ANNOTATIONS (classification 'Public'),
    run_id        VARCHAR2(40)   NOT NULL ANNOTATIONS (classification 'Internal'),
    file_id       NUMBER                  ANNOTATIONS (classification 'Internal'),
    status        VARCHAR2(10)   NOT NULL ANNOTATIONS (classification 'Internal'),
    started_at    TIMESTAMP      NOT NULL ANNOTATIONS (classification 'Internal'),
    finished_at   TIMESTAMP      NOT NULL ANNOTATIONS (classification 'Internal'),
    rows_in_file  NUMBER                  ANNOTATIONS (classification 'Internal'),
    inserted      NUMBER                  ANNOTATIONS (classification 'Internal'),
    revised       NUMBER                  ANNOTATIONS (classification 'Internal'),
    unchanged     NUMBER                  ANNOTATIONS (classification 'Internal'),
    skipped       NUMBER                  ANNOTATIONS (classification 'Internal'),
    db_user       VARCHAR2(128)  NOT NULL ANNOTATIONS (classification 'Internal'),
    message       VARCHAR2(4000)          ANNOTATIONS (classification 'Internal'),
    CONSTRAINT load_audit_pk PRIMARY KEY (load_id),
    CONSTRAINT load_audit_status_ck CHECK (status IN ('success', 'failed'))
) ANNOTATIONS (classification 'Internal')
/
-- Work table for one file at a time, private to the session.
CREATE GLOBAL TEMPORARY TABLE IF NOT EXISTS incoming_observation (
    ref_date      DATE           NOT NULL ANNOTATIONS (classification 'Public'),
    value         NUMBER         NOT NULL ANNOTATIONS (classification 'Public'),
    CONSTRAINT incoming_observation_pk PRIMARY KEY (ref_date)
) ON COMMIT DELETE ROWS ANNOTATIONS (classification 'Internal')
/
-- Data dictionary: one row per column of every permanent table, refreshed from Oracle's catalog
-- by setup (refresh_data_dictionary in 03_views.sql). It describes itself too.
CREATE TABLE IF NOT EXISTS data_dictionary (
    table_name            VARCHAR2(128)  NOT NULL ANNOTATIONS (classification 'Internal'),
    table_description     VARCHAR2(4000)          ANNOTATIONS (classification 'Internal'),
    table_classification  VARCHAR2(30)            ANNOTATIONS (classification 'Internal'),
    column_id             NUMBER         NOT NULL ANNOTATIONS (classification 'Internal'),
    column_name           VARCHAR2(128)  NOT NULL ANNOTATIONS (classification 'Internal'),
    data_type             VARCHAR2(128)  NOT NULL ANNOTATIONS (classification 'Internal'),
    nullable              CHAR(1)        NOT NULL ANNOTATIONS (classification 'Internal'),
    column_description    VARCHAR2(4000)          ANNOTATIONS (classification 'Internal'),
    column_classification VARCHAR2(30)            ANNOTATIONS (classification 'Internal'),
    refreshed_at          TIMESTAMP      NOT NULL ANNOTATIONS (classification 'Internal'),
    CONSTRAINT data_dictionary_pk PRIMARY KEY (table_name, column_name)
) ANNOTATIONS (classification 'Internal')
/
COMMENT ON TABLE source_system IS 'Publishers of the open data held here, with their terms of use.'
/
COMMENT ON COLUMN source_system.source_code IS 'Short code of the source: valet (Bank of Canada) or statcan (Statistics Canada).'
/
COMMENT ON COLUMN source_system.name IS 'Name of the publisher.'
/
COMMENT ON COLUMN source_system.terms_url IS 'Terms of use and attribution requirements of the publisher.'
/
COMMENT ON TABLE series IS 'Reference list of the series held, copied from config/series.yml on every load.'
/
COMMENT ON COLUMN series.series_key IS 'Project key of the series, for example usd_cad.'
/
COMMENT ON COLUMN series.source_code IS 'Publisher of the series.'
/
COMMENT ON COLUMN series.series_id IS 'Identifier at the publisher: Valet series name or StatCan vector ID.'
/
COMMENT ON COLUMN series.product_id IS 'StatCan table (product) ID; NULL for Bank of Canada series.'
/
COMMENT ON COLUMN series.name IS 'Human-readable name of the series.'
/
COMMENT ON COLUMN series.unit IS 'Unit of the values, for example percent.'
/
COMMENT ON COLUMN series.frequency IS 'daily or monthly.'
/
COMMENT ON COLUMN series.start_date IS 'First period held; earlier periods in a payload are not loaded.'
/
COMMENT ON COLUMN series.updated_at IS 'When this row was last written from the configuration.'
/
COMMENT ON TABLE landed_file IS 'Every API response loaded, kept unchanged as received, so any load can be replayed and audited.'
/
COMMENT ON COLUMN landed_file.file_id IS 'Surrogate key of the landed file.'
/
COMMENT ON COLUMN landed_file.series_key IS 'Series the response belongs to.'
/
COMMENT ON COLUMN landed_file.run_id IS 'Ingestion run that fetched the response (also its file name in data/raw).'
/
COMMENT ON COLUMN landed_file.received_at IS 'When the response was fetched from the API (UTC, from the run id).'
/
COMMENT ON COLUMN landed_file.sha256 IS 'SHA-256 of the payload bytes as received, for tamper evidence.'
/
COMMENT ON COLUMN landed_file.payload IS 'The API response as received (JSON).'
/
COMMENT ON COLUMN landed_file.loaded_at IS 'When the file was loaded into this database (UTC).'
/
COMMENT ON COLUMN landed_file.loaded_by IS 'Database user whose session loaded the file.'
/
COMMENT ON TABLE observation_revision IS 'Effective-dated history of every published value: what was known about each period, and when.'
/
COMMENT ON COLUMN observation_revision.series_key IS 'Series of the observation.'
/
COMMENT ON COLUMN observation_revision.ref_date IS 'Reference period: the day for daily series, the first day of the month for monthly series.'
/
COMMENT ON COLUMN observation_revision.value IS 'Value as published, in the unit of the series.'
/
COMMENT ON COLUMN observation_revision.known_from IS 'When this value was first received (UTC). Start of the period during which it was the known value.'
/
COMMENT ON COLUMN observation_revision.known_to IS 'When a revised value replaced it (UTC); NULL while it is the current value.'
/
COMMENT ON COLUMN observation_revision.file_id IS 'Landed file that first carried this value.'
/
COMMENT ON COLUMN observation_revision.closed_by_file_id IS 'Landed file that carried the revised value; NULL while current.'
/
COMMENT ON TABLE load_audit IS 'One row per attempt to load a landed file, successful or not.'
/
COMMENT ON COLUMN load_audit.load_id IS 'Surrogate key of the load attempt.'
/
COMMENT ON COLUMN load_audit.series_key IS 'Series of the file.'
/
COMMENT ON COLUMN load_audit.run_id IS 'Ingestion run that fetched the file.'
/
COMMENT ON COLUMN load_audit.file_id IS 'Landed file loaded; NULL when the attempt failed.'
/
COMMENT ON COLUMN load_audit.status IS 'success or failed. A failed attempt changes no data.'
/
COMMENT ON COLUMN load_audit.started_at IS 'Start of the attempt (UTC).'
/
COMMENT ON COLUMN load_audit.finished_at IS 'End of the attempt (UTC).'
/
COMMENT ON COLUMN load_audit.rows_in_file IS 'Observations with a value in the file, at or after the series start date.'
/
COMMENT ON COLUMN load_audit.inserted IS 'Periods seen for the first time.'
/
COMMENT ON COLUMN load_audit.revised IS 'Periods whose value changed: the old revision was closed and a new one opened.'
/
COMMENT ON COLUMN load_audit.unchanged IS 'Periods whose value was already known.'
/
COMMENT ON COLUMN load_audit.skipped IS 'Entries in the file with no value, or before the series start date.'
/
COMMENT ON COLUMN load_audit.db_user IS 'Database user whose session ran the load.'
/
COMMENT ON COLUMN load_audit.message IS 'Error message of a failed attempt.'
/
COMMENT ON TABLE incoming_observation IS 'Session-private work table: the observations parsed from the file being loaded.'
/
COMMENT ON COLUMN incoming_observation.ref_date IS 'Reference period parsed from the file.'
/
COMMENT ON COLUMN incoming_observation.value IS 'Value parsed from the file.'
/
COMMENT ON TABLE data_dictionary IS 'Description and classification of every column of every table, read from the Oracle catalog.'
/
COMMENT ON COLUMN data_dictionary.table_name IS 'Table the column belongs to.'
/
COMMENT ON COLUMN data_dictionary.table_description IS 'Comment of the table.'
/
COMMENT ON COLUMN data_dictionary.table_classification IS 'Classification annotation of the table.'
/
COMMENT ON COLUMN data_dictionary.column_id IS 'Position of the column in the table.'
/
COMMENT ON COLUMN data_dictionary.column_name IS 'Name of the column.'
/
COMMENT ON COLUMN data_dictionary.data_type IS 'Oracle data type of the column.'
/
COMMENT ON COLUMN data_dictionary.nullable IS 'Y if the column accepts NULL, N if not.'
/
COMMENT ON COLUMN data_dictionary.column_description IS 'Comment of the column.'
/
COMMENT ON COLUMN data_dictionary.column_classification IS 'Classification annotation of the column: Public or Internal.'
/
COMMENT ON COLUMN data_dictionary.refreshed_at IS 'When setup last read the catalog (UTC).'
/
MERGE INTO source_system t
USING (
    SELECT 'valet' AS source_code, 'Bank of Canada (Valet API)' AS name,
           'https://www.bankofcanada.ca/terms/' AS terms_url FROM dual
    UNION ALL
    SELECT 'statcan', 'Statistics Canada (Web Data Service)',
           'https://www.statcan.gc.ca/en/terms-conditions/open-licence' FROM dual
) s
ON (t.source_code = s.source_code)
WHEN MATCHED THEN UPDATE SET t.name = s.name, t.terms_url = s.terms_url
WHEN NOT MATCHED THEN INSERT (source_code, name, terms_url) VALUES (s.source_code, s.name, s.terms_url)
/
COMMIT
/
