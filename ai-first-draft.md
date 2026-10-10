---
lab3_first_draft:
  source: ai
  tool: "ChatGPT (GPT-5.6 Sol), ChatGPT chat, 2026-10-10"
  ladder: [0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0]
  verdict: TODO
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
lab3_flawed_ladder:
  verdict: refuted
  evidence: {p99_seconds: TODO, bucket: [TODO, TODO], relative_width: TODO}
---
<!-- ai-generated: 80% - AI supplied the first draft and helped structure the file; I review the evidence and verdicts -->

# The assistant's first draft, and two verdicts

## Prompt

For a FastAPI service endpoint GET /kb/search that calls an upstream knowledge-base index, propose a Prometheus histogram bucket ladder in seconds for request latency and one alert rule for the endpoint. I have not measured the latency distribution yet. Give concrete bucket boundaries and explain the alert rule.

## Answer

For an unmeasured FastAPI endpoint, I would start with a broad latency histogram and then refine it after observing real traffic.

Suggested Prometheus histogram buckets, in seconds:

```text
0.005
0.01
0.025
0.05
0.1
0.25
0.5
1.0
2.5
5.0
```

This ladder gives relatively fine resolution for fast requests while still covering slow upstream responses. Because the latency distribution has not been measured yet, these should be treated as an initial guess rather than the final production buckets.

For example, if the metric is:

```text
http_request_duration_seconds_bucket{route="/kb/search", ...}
```

a p99 latency alert could be:

```yaml
- alert: KBSearchHighP99Latency
  expr: |
    histogram_quantile(
      0.99,
      sum by (le) (
        rate(http_request_duration_seconds_bucket{route="/kb/search"}[5m])
      )
    ) > 0.5
  for: 10m
  labels:
    severity: warning
  annotations:
    summary: "High p99 latency on GET /kb/search"
    description: "The 99th percentile latency for /kb/search has been above 500 ms for 10 minutes."
```

The alert uses a five-minute rate window to calculate the recent latency distribution and fires only if p99 stays above 500 ms for ten minutes. The `for` period helps avoid paging on a short transient spike. Since no measurements are available yet, both the 500 ms threshold and the bucket boundaries should be validated against the actual latency distribution before being treated as final.

## Verdict on the draft ladder

TODO - fill after the first load 3 measurement.

## The draft alert rule

TODO - evaluate after the SLO and measured latency distribution are known.

## Verdict on the instructor's flawed ladder

TODO - fill after the first load 3 measurement.
