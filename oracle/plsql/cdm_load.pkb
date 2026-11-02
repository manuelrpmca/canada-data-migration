-- Load package body (ADR 0009). Run as the owner schema.
--
-- Why not a single MERGE: MERGE would overwrite a revised value in place and lose what was
-- known before. Here a revision closes the current row (known_to) and opens a new one, inside
-- one transaction per file, so the history answers "what was known on day X".
CREATE OR REPLACE PACKAGE BODY cdm_load AS

    -- Times are stored in UTC; the user is the session's, not the package owner's.
    -- Written in its own transaction, so the record survives the rollback of the failed load.
    PROCEDURE audit_failure(
        p_series_key IN VARCHAR2,
        p_run_id     IN VARCHAR2,
        p_started_at IN TIMESTAMP,
        p_message    IN VARCHAR2
    ) IS
        PRAGMA AUTONOMOUS_TRANSACTION;
    BEGIN
        INSERT INTO load_audit (series_key, run_id, status, started_at, finished_at, db_user, message)
        VALUES (p_series_key, p_run_id, 'failed', p_started_at, SYS_EXTRACT_UTC(SYSTIMESTAMP), SYS_CONTEXT('USERENV', 'SESSION_USER'),
                SUBSTR(p_message, 1, 4000));
        COMMIT;
    END;

    PROCEDURE sync_series(
        p_series_key   IN VARCHAR2,
        p_source_code  IN VARCHAR2,
        p_series_id    IN VARCHAR2,
        p_product_id   IN NUMBER,
        p_name         IN VARCHAR2,
        p_unit         IN VARCHAR2,
        p_frequency    IN VARCHAR2,
        p_start_date   IN DATE
    ) IS
    BEGIN
        MERGE INTO series t
        USING (SELECT p_series_key AS series_key FROM dual) s
        ON (t.series_key = s.series_key)
        WHEN MATCHED THEN UPDATE SET
            t.source_code = p_source_code, t.series_id = p_series_id,
            t.product_id = p_product_id, t.name = p_name, t.unit = p_unit,
            t.frequency = p_frequency, t.start_date = p_start_date, t.updated_at = SYS_EXTRACT_UTC(SYSTIMESTAMP)
        WHEN NOT MATCHED THEN INSERT
            (series_key, source_code, series_id, product_id, name, unit, frequency, start_date,
             updated_at)
        VALUES
            (p_series_key, p_source_code, p_series_id, p_product_id, p_name, p_unit, p_frequency,
             p_start_date, SYS_EXTRACT_UTC(SYSTIMESTAMP));
        COMMIT;
    END;

    FUNCTION is_loaded(p_series_key IN VARCHAR2, p_run_id IN VARCHAR2) RETURN NUMBER IS
        l_count NUMBER;
    BEGIN
        SELECT COUNT(*) INTO l_count
        FROM landed_file
        WHERE series_key = p_series_key AND run_id = p_run_id;
        RETURN l_count;
    END;

    -- Parse the payload into INCOMING_OBSERVATION with the same rules as the Python parsers
    -- (src/cdm/sources): entries without a value are skipped, the last entry wins if a date
    -- repeats. Periods before the series start date are skipped as well.
    PROCEDURE parse_payload(
        p_source_code IN  VARCHAR2,
        p_start_date  IN  DATE,
        p_payload     IN  CLOB,
        o_rows        OUT NUMBER,
        o_entries     OUT NUMBER
    ) IS
        l_not_success NUMBER;
    BEGIN
        DELETE FROM incoming_observation;
        IF p_source_code = 'valet' THEN
            -- {"observations": [{"d": "YYYY-MM-DD", "<series>": {"v": "1.23"}}, ...]}
            INSERT INTO incoming_observation (ref_date, value)
            SELECT ref_date, value
            FROM (
                SELECT TO_DATE(jt.d, 'YYYY-MM-DD') AS ref_date, jt.v AS value,
                       ROW_NUMBER() OVER (PARTITION BY jt.d ORDER BY jt.n DESC) AS rn
                FROM JSON_TABLE(p_payload, '$.observations[*]'
                         COLUMNS (n FOR ORDINALITY,
                                  d VARCHAR2(10) PATH '$.d',
                                  v NUMBER PATH '$.*.v' NULL ON ERROR)) jt
                WHERE jt.v IS NOT NULL
            )
            WHERE rn = 1 AND ref_date >= p_start_date;
            o_rows := SQL%ROWCOUNT;
            SELECT COUNT(*) INTO o_entries
            FROM JSON_TABLE(p_payload, '$.observations[*]' COLUMNS (n FOR ORDINALITY));
        ELSIF p_source_code = 'statcan' THEN
            -- [{"status": "SUCCESS", "object": {"vectorDataPoint": [{"refPer", "value"}, ...]}}]
            SELECT COUNT(*) INTO l_not_success
            FROM JSON_TABLE(p_payload, '$[*]' COLUMNS (status VARCHAR2(30) PATH '$.status'))
            WHERE status IS NULL OR status <> 'SUCCESS';
            IF l_not_success > 0 THEN
                RAISE_APPLICATION_ERROR(-20002, 'WDS response reports a status other than SUCCESS');
            END IF;
            INSERT INTO incoming_observation (ref_date, value)
            SELECT ref_date, value
            FROM (
                SELECT TO_DATE(SUBSTR(jt.ref_per, 1, 10), 'YYYY-MM-DD') AS ref_date,
                       jt.v AS value,
                       ROW_NUMBER() OVER (PARTITION BY SUBSTR(jt.ref_per, 1, 10)
                                          ORDER BY jt.item DESC, jt.n DESC) AS rn
                FROM JSON_TABLE(p_payload, '$[*]'
                         COLUMNS (item FOR ORDINALITY,
                                  NESTED PATH '$.object.vectorDataPoint[*]'
                                  COLUMNS (n FOR ORDINALITY,
                                           ref_per VARCHAR2(30) PATH '$.refPer',
                                           v NUMBER PATH '$.value' NULL ON ERROR))) jt
                WHERE jt.v IS NOT NULL AND jt.ref_per IS NOT NULL
            )
            WHERE rn = 1 AND ref_date >= p_start_date;
            o_rows := SQL%ROWCOUNT;
            SELECT COUNT(*) INTO o_entries
            FROM JSON_TABLE(p_payload, '$[*].object.vectorDataPoint[*]'
                     COLUMNS (n FOR ORDINALITY));
        ELSE
            RAISE_APPLICATION_ERROR(-20004, 'Unknown source: ' || p_source_code);
        END IF;
    END;

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
    ) IS
        l_started     TIMESTAMP := SYS_EXTRACT_UTC(SYSTIMESTAMP);
        l_source_code series.source_code%TYPE;
        l_start_date  series.start_date%TYPE;
        l_last        TIMESTAMP;
        l_file_id     NUMBER;
        l_rows        NUMBER;
        l_entries     NUMBER;
        l_message     VARCHAR2(4000);
    BEGIN
        SAVEPOINT before_load;
        BEGIN
            SELECT source_code, start_date INTO l_source_code, l_start_date
            FROM series WHERE series_key = p_series_key;
        EXCEPTION
            WHEN NO_DATA_FOUND THEN
                RAISE_APPLICATION_ERROR(-20003, 'Unknown series: ' || p_series_key);
        END;

        SELECT MAX(received_at) INTO l_last FROM landed_file WHERE series_key = p_series_key;
        IF l_last IS NOT NULL AND p_received_at <= l_last THEN
            RAISE_APPLICATION_ERROR(-20001,
                'Out of order: run ' || p_run_id || ' was received at '
                || TO_CHAR(p_received_at, 'YYYY-MM-DD"T"HH24:MI:SS')
                || ', not after the last file loaded for ' || p_series_key || ' ('
                || TO_CHAR(l_last, 'YYYY-MM-DD"T"HH24:MI:SS') || ')');
        END IF;

        INSERT INTO landed_file (series_key, run_id, received_at, sha256, payload, loaded_at, loaded_by)
        VALUES (p_series_key, p_run_id, p_received_at, LOWER(p_sha256), p_payload, SYS_EXTRACT_UTC(SYSTIMESTAMP),
                SYS_CONTEXT('USERENV', 'SESSION_USER'))
        RETURNING file_id INTO l_file_id;

        parse_payload(l_source_code, l_start_date, p_payload, l_rows, l_entries);

        SELECT COUNT(CASE WHEN r.ref_date IS NULL THEN 1 END),
               COUNT(CASE WHEN r.ref_date IS NOT NULL AND r.value <> i.value THEN 1 END)
        INTO o_inserted, o_revised
        FROM incoming_observation i
        LEFT JOIN observation_revision r
          ON r.series_key = p_series_key AND r.ref_date = i.ref_date AND r.known_to IS NULL;
        o_unchanged := l_rows - o_inserted - o_revised;
        o_skipped := l_entries - l_rows;

        -- Close the current revision of every period whose value changed...
        UPDATE observation_revision r
        SET r.known_to = p_received_at, r.closed_by_file_id = l_file_id
        WHERE r.series_key = p_series_key
          AND r.known_to IS NULL
          AND EXISTS (SELECT 1 FROM incoming_observation i
                      WHERE i.ref_date = r.ref_date AND i.value <> r.value);

        -- ...then open a revision for every period without a current one (new or just closed).
        INSERT INTO observation_revision (series_key, ref_date, value, known_from, file_id)
        SELECT p_series_key, i.ref_date, i.value, p_received_at, l_file_id
        FROM incoming_observation i
        WHERE NOT EXISTS (SELECT 1 FROM observation_revision r
                          WHERE r.series_key = p_series_key
                            AND r.ref_date = i.ref_date
                            AND r.known_to IS NULL);

        INSERT INTO load_audit (series_key, run_id, file_id, status, started_at, finished_at,
                                rows_in_file, inserted, revised, unchanged, skipped, db_user)
        VALUES (p_series_key, p_run_id, l_file_id, 'success', l_started, SYS_EXTRACT_UTC(SYSTIMESTAMP),
                l_rows, o_inserted, o_revised, o_unchanged, o_skipped, SYS_CONTEXT('USERENV', 'SESSION_USER'))
        RETURNING load_id INTO o_load_id;

        COMMIT;
    EXCEPTION
        WHEN OTHERS THEN
            l_message := SQLERRM;
            ROLLBACK TO before_load;
            audit_failure(p_series_key, p_run_id, l_started, l_message);
            RAISE;
    END;

END cdm_load;
/
