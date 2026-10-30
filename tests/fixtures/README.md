# Test fixtures

**These files are recorded from the live APIs on 2026-10-30, then trimmed** to a few observations so
they stay readable in a diff. Values are real; only the length of the `observations` /
`vectorDataPoint` arrays was cut, and the files were re-serialized with Python's `json` module, so they
are not byte-identical to the original responses.

| File | Source | Request |
| --- | --- | --- |
| `valet_observations.json` | Bank of Canada Valet | `GET /valet/observations/FXUSDCAD/json?start_date=2026-10-15`, first 4 of 11 observations |
| `statcan_vector_data.json` | Statistics Canada WDS | `POST /getDataFromVectorsAndLatestNPeriods` for vector 41691919 (CPI all-items, Ontario), first 3 of 5 periods |

The recorded responses contain no empty Valet cells and no null WDS values. The tests that check those
cases use small inline payloads in `tests/unit/test_sources.py`, marked as synthetic.

Data: Bank of Canada ([terms](https://www.bankofcanada.ca/terms/)); Statistics Canada, reproduced and
distributed on an "as is" basis with the permission of Statistics Canada
([Open Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence)).
