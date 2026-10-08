# Data layer fixes (protellect_data.py)

## Why sources were empty for TP53
| Source | Cause | Fix |
|---|---|---|
| DGIdb | Called the retired v2 REST API (DGIdb v5 is GraphQL) | v5 GraphQL query, legacy endpoint only as a fallback |
| UniProt isoforms | Looked for comment type `ALTERNATIVE SEQUENCE`; UniProt uses `ALTERNATIVE PRODUCTS` | Correct type (both accepted) |
| Open Targets | One query asked for fields that no longer exist, so the whole reply was an error that was swallowed; tractability was keyed `SM`/`AB`/`PR` but the app reads `Small molecule`/`Antibody`/`PROTAC`; `q=TP53` free-text could resolve the wrong gene | Four separate section queries, each with fallback variants; codes mapped; exact `symbol:` match with an Ensembl fallback; section errors returned under `_errors` |
| ClinGen | Returned `classifications` but the app reads `classification` (never present); endpoint is a web page, not JSON | Returns both; uses the official bulk download, cached for a day |
| PubMed / "Europe PMC" step | 36 calls, no retry, no API key, no rate limit (NCBI allows 3/s), so bursts got HTTP 429 that became silent empties. (The trace label says Europe PMC but that fetcher calls NCBI PubMed.) | Retry with backoff, 3/s throttle, optional `NCBI_API_KEY` (10/s) |
| All | Bare `except: return []` hid every failure, and the empty result was **cached** for 1-24 hours | Failures are recorded in `FETCH_ERRORS`, shown in the app, and never cached |

## What to do
1. Replace `protellect_data.py` and the `protellect_core` folder, reboot.
2. Add a free NCBI key to Streamlit secrets: `NCBI_API_KEY = "..."` (and optionally `NCBI_EMAIL`). Without it, bursts of NCBI calls can still be rate limited.
3. Open any tab -> "Data audit" -> **Check data sources now**. It calls each source from your server and shows HTTP status, time and the exact error.

## Be clear about what was and was not tested
Tested with simulated API replies (17 tests in `test_protellect_data.py`), including failures: wrong-gene resolution, code mapping, one bad field not blanking the rest,
retry and throttling, key sent only to NCBI, failures not cached. NOT tested against the live services (none are reachable from where I work). The endpoint and
field names come from each service's documented behaviour as I know it; if one has changed, "Check data sources now" will name the exact field or status.
