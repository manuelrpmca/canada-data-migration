# 0003. Data sources and initial series

- Status: Accepted
- Date: 2026-10-29
- Milestone: M0

## Context

The project needs real, public, Canadian data that updates on its own, can be used commercially with attribution, and needs no paid account. Mixing daily and monthly series is useful: it forces real modelling decisions (calendar dimension, aggregation) instead of a single flat table.

Facts checked on 2026-10-29:

- **Bank of Canada Valet API.** No registration, key or cost. Formats: JSON, CSV, XML. The Bank asks clients to ramp up request rates gradually, back off on failure, and cache data that updates once a day. Source: [Valet API how-to](https://www.bankofcanada.ca/valet-api-how-to/). Use is subject to the Bank's [terms of use](https://www.bankofcanada.ca/terms/).
- **Statistics Canada Web Data Service (WDS).** REST base URL `https://www150.statcan.gc.ca/t1/wds/rest/`. Limits: 50 requests per second overall and 25 per second per IP. Data is published every business day at 8:30 a.m. Eastern; between midnight and 8:30 a.m. some tables are locked and the service may answer HTTP 409. Methods include `getDataFromVectorsAndLatestNPeriods`, `getDataFromVectorByReferencePeriodRange`, `getSeriesInfoFromCubePidCoord` and `getFullTableDownloadCSV`. Source: [WDS user guide](https://www.statcan.gc.ca/en/developers/wds/user-guide).
- **Statistics Canada Open Licence** allows reuse with the attribution "Adapted from Statistics Canada, name of product, reference date" plus a non-endorsement statement. Source: [Open Licence](https://www.statcan.gc.ca/en/terms-conditions/open-licence).

## Options considered

1. **Bank of Canada + Statistics Canada APIs** (recommended in the project brief). Official, free, keyless, daily and monthly frequencies.
2. **Open Government Portal (CKAN) datasets.** Broad, but mostly static files; less of an "incremental ingestion" story.
3. **City of Toronto open data (TTC, 311).** Good for analytics, but positions the project as analysis rather than migration.

## Decision

Use the Bank of Canada Valet API and the Statistics Canada WDS. Start v0.1 with **four series**, enough to exercise two sources and two frequencies without slowing the first release:

| Source | Indicator | Frequency | Identifier |
| --- | --- | --- | --- |
| Bank of Canada | USD/CAD daily exchange rate | Daily (business days) | `FXUSDCAD` |
| Bank of Canada | Target for the overnight rate (policy rate) | Changes on announcement dates | `V39079` |
| Statistics Canada | Consumer Price Index, all-items, Ontario | Monthly | Table 18-10-0004-01, vector looked up in M1 |
| Statistics Canada | Unemployment rate, Ontario, seasonally adjusted | Monthly | Labour Force Survey table, vector looked up in M1 |

Series identifiers above come from prior knowledge, not from a live call (the planning environment had no access to the APIs). **M1 starts by confirming each identifier against the live API** (Valet's series list, WDS `getSeriesInfoFromCubePidCoord`) and recording the confirmed vector IDs and table titles in `config/series.yml` and in the M1 note. If an identifier turns out to be wrong, the fix is recorded there; the decision (which indicators) stands. Housing indicators are a candidate for v1.0.

## Consequences

- No secrets are needed for v0.1.
- The ingestion client must respect both sources' guidance: gentle request rates, retries with exponential back-off and jitter, and treating StatCan's HTTP 409 as "try later", not as failure.
- The scheduled run should start after 8:30 a.m. Eastern so StatCan data for the day is available.
- Every published chart or report must carry the attribution lines above.
