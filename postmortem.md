---
lab4_postmortem:
  ticket: "1224ad8d-06a8-4ae3-865a-da2015a4ddb5"
  detecting_alert: ShopCheckoutErrors
  onset: 2026-10-12T07:05:45Z
  detection: 2026-10-12T07:09:19Z
  acknowledgement: 2026-10-12T07:10:07Z
  recovery: 2026-10-12T07:12:19Z
  mttd_seconds: 214
  mtta_seconds: 48
  mttr_seconds: 394
  identified_flags: [productCatalogFailure, adManualGc, recommendationCacheFailure]
---
<!-- ai-generated: 90% - Claude Code drafted this postmortem from my Lab 4 recording and verified Prometheus evidence; I reviewed the checker-sensitive values. -->

# Postmortem: some shop orders and product pages failed while ads and pages slowed down

## Date

The incident happened on Monday 2026-10-12 between 07:05:45Z and 07:13:20Z (recording `lab4-rec-3`, run
`fe6ecd21acce7a08`). This postmortem was written on 2026-10-25 from the recorded snapshot and ticket.

## Authors

Iwona Szukala, acting as the on-call engineer for this recorded incident. The page, the ticket and the rollback were
recorded by the course team; the investigation, the flag identification and this document are mine.

## Status

Complete for the incident: service was restored and the detecting alert resolved. Action items are open, and the
problem record below stays open until the underlying faults are removed.

## Summary

For about seven and a half minutes, a share of the shop's product page views, recommendation requests and orders
failed because product-catalog answered some GetProduct calls with errors, while the ad service paused for garbage
collection and recommendation's cache misbehaved. Checkout errors paged the on-call 3 min 34 s after the onset, and
the fault was rolled back at 07:13:20Z.

## Impact

- **Orders**: checkout's `PlaceOrder` SERVER spans failed at up to 9.8 % (07:09) and about 6 % afterwards; over the
  10 minutes to 07:15:00Z about 2 of 66 orders failed.
  Query: `sum(increase(traces_span_metrics_calls_total{service_name="checkout", span_kind="SPAN_KIND_SERVER", status_code="STATUS_CODE_ERROR"}[10m]))`
  against the same without `status_code`, at 07:15:00Z (2.2 of 65.5).
- **Shop front end**: about 83 of 2,296 frontend requests (3.6 %) failed in the same 10 minutes, peaking at a 7.2 %
  error ratio at 07:11. The failures were product pages (`GET /api/products/[productId]/index`, 0.17/s),
  recommendations (`GET /api/recommendations`, 0.10/s) and checkout (`POST /api/checkout`, 0.016/s) at 07:11.
  Query: `sum by (span_name) (rate(traces_span_metrics_calls_total{service_name="frontend", span_kind="SPAN_KIND_SERVER", status_code="STATUS_CODE_ERROR"}[5m]))`.
- **Latency**: frontend p95 rose from about 35 ms to 620 ms, and ad's p95 from 3.9 ms to 780 ms from 07:07 on.
  Query: `histogram_quantile(0.95, sum by (le) (rate(traces_span_metrics_duration_milliseconds_bucket{service_name="ad", span_kind="SPAN_KIND_SERVER"}[5m])))`.
  Checkout's own latency did not change (p95 48 ms throughout).
- No data was lost; failed orders were not charged (payment had no failed calls).

## Root Causes

Three faults were active at the same time, one per class of the injector's pool:

1. `productCatalogFailure` (errors): product-catalog failed GetProduct for some products - 0.149 failed SERVER
   calls/s at 07:11, none before the onset. Checkout's CLIENT GetProduct calls failed at 0.0082/s, exactly the rate of
   failed orders, and the frontend's product and recommendation pages failed with it.
2. `adManualGc` (latency): the ad service's JVM spent 0.115 s per second in garbage collection (about 2.1 collections
   per second) from 07:07 on, against zero on the baseline, and its p95 jumped to 780 ms, slowing the frontend.
3. `recommendationCacheFailure` (resources): recommendation's ratio of product-catalog `ListProducts` calls to
   `ListRecommendations` requests fell from exactly 1.0 to about 0.5, the signature of its cache being switched on with
   about half the requests served from a growing cache, and its RSS grew steadily from 72.96 MB to 73.86 MB.

Rejected with data: payment errors (none), ad errors (none), shipping slowness (p99 unchanged at about 3.9 ms),
catalog lock contention (product-catalog p99 unchanged at about 9 ms), homepage flood (frontend traffic 4.26/s ->
4.05/s), and the email memory leak (email container flat at 62 MB, no restart).

## Trigger

At 07:05:45Z (the onset) the fault injector switched the three feature flags on simultaneously after its 10-minute
healthy baseline. No deployment or configuration change by the shop's teams was involved; the flags were the change.

## Resolution

The three flags were switched back off through the injector, which is the workaround: the injector's
`seeded_fault_active` went from 1 to 0 between 07:13:15Z and 07:13:20Z. The recording does not show the order in which
the individual flags were switched off, because the shop's metrics arrive once a minute in 5-minute windows. After
the rollback all error series fell back to zero and ad's GC rate decayed with its window.

## Detection

The recorded rule `ShopCheckoutErrors` (P1, `service=checkout`, `system=shop`) started firing at 07:09:19Z, 214 s
(MTTD) after the onset, and paged: `itsm_pager_notifications_total{receiver="pager",status="firing"}` rose by 07:10:00Z.
The P1 ticket was opened at 07:09:37Z and acknowledged at 07:10:07Z, 48 s (MTTA) after the page. The P2
`ShopServiceErrors` alerts for checkout, frontend, frontend-proxy and product-catalog fired alongside it. Most of the
MTTD is structural: span metrics arrive once a minute and need a 5-minute window. Without the page, customers would
have noticed first - failed product pages are visible immediately. My own rule `CheckoutErrorRate` would have been
true from 07:08:20Z and fired at about 07:09:20Z with its `for: 1m`; the frontend's P3 latency rule would have caught
the ad slowdown, which no checkout alert can see.

## Action Items

| Action Item | Type | Owner | Bug |
|---|---|---|---|
| Add a P2 alert on any service's SERVER error ratio above 2 % (per `service_name`) so that product-catalog is named directly, not only through checkout | prevent | on-call (Iwona Szukala) | ITSM-41 |
| Alert on JVM GC time per second (`jvm_gc_duration_seconds_sum`) above 0.05 s/s for the ad service | prevent | ad service owner | ITSM-42 |
| Record a runbook step: on a checkout page, first check failing downstream CLIENT spans of checkout, then the feature flags | process | SRE team | ITSM-43 |
| Add a feature-flag change annotation to the shop dashboard so "what changed?" is answered at a glance | mitigate | platform team | ITSM-44 |

## Lessons Learned

### What went well

The P1 on checkout's error ratio paged within one evaluation of the symptom crossing its threshold, the ticket was
acknowledged 48 s after the page, and the P2 alerts already pointed at product-catalog as the deepest failing service.

### What went wrong

The detecting alert resolved at 07:12:19Z, about a minute before the fault ended, so MTTR reports a recovery that the
users did not yet have. Nothing alerted on the ad slowdown or the recommendation cache, which only showed up in
runtime metrics. The AI investigator stayed on checkout's counters and guessed payment from general knowledge.

### Where we got lucky

`productCatalogFailure` hit only one product in ten, and payment was healthy, so most orders went through. Had the
draw paired the catalog failure with a payment failure, checkout's error ratio would have been several times higher.

## Timeline

All times UTC, 2026-10-12.

- 06:53:15 - the injector starts its baseline; all shop error series empty, frontend p95 about 35 ms.
- 07:00:45 - last healthy reference point (onset minus 5 min): no failing SERVER spans in any service.
- 07:05:45 - **onset**: the three flags switch on (`seeded_fault_active` first sample).
- 07:07:00 - ad's GC rate starts rising and its p95 reaches 695 ms; frontend error ratio crosses 2 % at 07:07:20.
- 07:09:19 - **detection**: `ShopCheckoutErrors` (P1) fires; the pager receives the page.
- 07:09:37 - P1 ticket `1224ad8d-06a8-4ae3-865a-da2015a4ddb5` created.
- 07:10:07 - **acknowledgement** of the ticket.
- 07:11:00 - investigation: AI ledger entry H2 (the failure originates in product-catalog GetProduct) tested with
  `sum(rate(traces_span_metrics_calls_total{service_name="product-catalog", span_kind="SPAN_KIND_SERVER", span_name="oteldemo.ProductCatalogService/GetProduct", status_code="STATUS_CODE_ERROR"}[5m])) > 0.05 and on() sum(rate(traces_span_metrics_calls_total{service_name="checkout", span_kind="SPAN_KIND_CLIENT", span_name="oteldemo.ProductCatalogService/GetProduct", status_code="STATUS_CODE_ERROR"}[5m])) > 0`,
  which returned 0.149 at 07:11:00 and nothing at 07:00:45: confirmed. Entry H3 (payment Charge) tested with
  `sum(rate(traces_span_metrics_calls_total{service_name="payment", status_code="STATUS_CODE_ERROR"}[5m])) > 0`,
  which returned nothing: refuted, payment was not touched.
- 07:12:19 - **recovery**: `ShopCheckoutErrors` resolves (end of its firing run).
- 07:13:15-07:13:20 - the last flag is switched off; `seeded_fault_active` returns to 0.
- 07:14:45 - end of the snapshot; frontend latency decaying with its 5-minute window.

## Supporting information

- `itsmlab incident 4` output: run `fe6ecd21acce7a08`, onset 07:05:45Z, detection 07:09:19Z (`ShopCheckoutErrors`),
  acknowledgement 07:10:07Z, recovery 07:12:19Z, MTTD 214 s, MTTA 48 s, MTTR 394 s.
- Snapshot `incident/tsdb-snapshot.tar.gz` and ticket `incident/ticket.json` of recording `lab4-rec-3`.
- AI ledger `ai-rca-eval.json` (H1 partially_correct, H2 correct, H3 and H4 hallucinated) scoring
  `ai-rca/transcript.md`.
- Resource evidence: `sum by (service_name) (rate(jvm_gc_duration_seconds_sum[5m]))` (ad 0 -> 0.115 s/s);
  `sum(rate(traces_span_metrics_calls_total{service_name="recommendation",span_name="oteldemo.ProductCatalogService/ListProducts"}[5m])) / sum(rate(traces_span_metrics_calls_total{service_name="recommendation",span_name="oteldemo.RecommendationService/ListRecommendations"}[5m]))`
  (1.0 -> 0.49); `max by (container_name) (container_memory_usage_total_bytes{container_name="email"})` (flat 62 MB).
- Alerting: `prometheus/demo-alerts.yml` and `alertmanager/alertmanager.yml` in this repository.

## Problem record

- Incident record: ticket 1224ad8d-06a8-4ae3-865a-da2015a4ddb5 (P1, acknowledged 07:10:07Z), closed when service was restored.
- Root cause: three faulty feature flags at once - product-catalog failing GetProduct, ad's manual GC pauses, and recommendation's runaway cache.
- Known error: when these flags are on, product-catalog fails one product in ten, ad pauses for GC and recommendation's memory grows; no code fix is deployed yet.
- Workaround: switch the three flags off through the injector (`POST /flags/<flag>/off`); service recovers within one 5-minute metrics window.
