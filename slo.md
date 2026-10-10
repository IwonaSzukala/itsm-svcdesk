---
lab3_slo:
  service: svcdesk
  route: /kb/search
  window: 28d
  slis:
    availability:
      objective: 0.99
      good: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search", http_response_status_code!~"5.."}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
    latency:
      objective: 0.99
      threshold_seconds: 0.2
      good: 'sum(rate(http_server_request_duration_seconds_bucket{job="svcdesk", http_route="/kb/search", le="0.2"}[5m]))'
      valid: 'sum(rate(http_server_request_duration_seconds_count{job="svcdesk", http_route="/kb/search"}[5m]))'
      error_budget: {fraction: 0.01, minutes: 403.2}
  alerts:
    - {alert: KbSearchAvailabilityBurnFast, sli: availability, burn_rate: 14.4, long_window: 1h, short_window: 5m}
    - {alert: KbSearchAvailabilityBurnSlow, sli: availability, burn_rate: 6, long_window: 6h, short_window: 30m}
---
<!-- ai-generated: 85% - AI drafted the SLO arithmetic and prose from my measured Lab 3 results; I reviewed the objectives and thresholds -->

# SLO for `GET /kb/search`

## Availability

The availability SLI is the share of valid `/kb/search` requests that do not return a 5xx response. I chose an objective of 0.99 over a 28-day window. This gives an error-budget fraction of 0.01, equal to 403.2 minutes over 28 days.

During my measured run the service returned 2391 successful responses and 9 responses with status 502, giving observed availability of about 99.625%. The failures come from the `kb-index` dependency as well as from the service path that depends on it, so an objective such as 99.9% would be stricter than the behaviour I actually measured. A 99% objective leaves some margin for the dependency's unavoidable failures while still making sustained upstream failures visible.

## Latency

The latency SLI is the share of valid `/kb/search` requests completed in at most 0.2 seconds. The threshold is a finite boundary in my histogram ladder, so the SLI counts requests directly instead of relying on interpolation.

The measured distribution had a p50 of about 30.4 ms, p99 of 168.8 ms, and p99.99 of about 200.2 ms. The directly measured `kb-index` p99 was 161.9 ms, showing that much of the high-latency tail comes from the dependency. I therefore chose 0.2 s as a threshold: it is above the measured p99 and covers the dependency's slow tail while remaining tight enough to detect a meaningful latency regression.

The latency objective is 0.99 over 28 days. Its error-budget fraction is 0.01, or 403.2 minutes. This objective is consistent with the distribution I measured and should not reject a release merely for reproducing normal dependency behaviour.

## Alerts

| alert | SLI | burn rate | long / short window | budget impact at threshold burn | severity |
|---|---|---:|---|---|---|
| KbSearchAvailabilityBurnFast | availability | 14.4 | 1h / 5m | about 2.14% of the total budget per hour; full budget in about 46.7h | P1 page |
| KbSearchAvailabilityBurnSlow | availability | 6 | 6h / 30m | about 5.36% of the total budget over six hours; full budget in about 112h | P2 chat |

The fast alert is P1 because a 14.4x burn sustained for long enough can consume the whole 28-day budget in less than two days. Waking a person for a short transient would be expensive, so the short window must confirm the problem, but once both windows show that burn rate, waiting until morning risks spending a substantial part of the remaining budget.

The slower 6x burn goes to P2 chat. It is serious enough to exhaust the budget in less than five days if it continues, but its longer windows indicate a slower-moving problem for which immediate overnight paging is less justified. It should still be investigated promptly during normal working hours.

## Buckets

The final histogram ladder is:

`0.005, 0.01, 0.02, 0.03, 0.04, 0.05, 0.075, 0.1, 0.12, 0.14, 0.15, 0.16, 0.17, 0.18, 0.19, 0.2, 0.22, 0.25, 0.3, 0.5, 1.0, 2.5, 5.0`

My measured p99 was 0.1688 s, so it lies in the bucket `(0.16, 0.17]`. That bucket is 0.01 s wide, giving a relative width of `0.01 / 0.1688 = 0.0592`, or about 5.92% of p99.

A plus-or-minus 10% band around the measured p99 is approximately 0.1519 to 0.1857 s. I placed boundaries at 0.15, 0.16, 0.17, 0.18 and 0.19 so this entire band is covered by narrow 10 ms buckets, comfortably below the 20% resolution limit.

I used additional boundaries below 0.1 s because most requests were much faster than the p99, with a measured median around 30 ms. Above 0.2 s the boundaries become progressively wider because those values are outside the normal measured tail and fine resolution there is less useful than preserving the boundary budget.
