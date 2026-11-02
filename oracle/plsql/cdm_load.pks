-- Load package of the governed system of record (ADR 0009). Run as the owner schema.
-- Definer's rights: callers need only EXECUTE on the package, never access to the tables.
CREATE OR REPLACE PACKAGE cdm_load AUTHID DEFINER AS

    -- Write one series from config/series.yml into the SERIES reference table.
    PROCEDURE sync_series(
        p_series_key   IN VARCHAR2,
        p_source_code  IN VARCHAR2,
        p_series_id    IN VARCHAR2,
        p_product_id   IN NUMBER,
        p_name         IN VARCHAR2,
        p_unit         IN VARCHAR2,
        p_frequency    IN VARCHAR2,
        p_start_date   IN DATE
    );

    -- 1 if the landed file of this run was already loaded for this series, else 0.
    FUNCTION is_loaded(p_series_key IN VARCHAR2, p_run_id IN VARCHAR2) RETURN NUMBER;

    -- Load one landed API response in its own transaction: keep the payload, parse it, and
    -- apply it to the effective-dated history (close revised values, open new ones).
    -- Files of a series must arrive in the order they were received. Every attempt is written
    -- to LOAD_AUDIT; a failed attempt changes no data and raises the error to the caller.
    PROCEDURE load_file(
        p_series_key   IN  VARCHAR2,
        p_run_id       IN  VARCHAR2,
        p_received_at  IN  TIMESTAMP,
        p_sha256       IN  VARCHAR2,
        p_payload      IN  CLOB,
        o_load_id      OUT NUMBER,
        o_inserted     OUT NUMBER,
        o_revised      OUT NUMBER,
        o_unchanged    OUT NUMBER,
        o_skipped      OUT NUMBER
    );

END cdm_load;
/
