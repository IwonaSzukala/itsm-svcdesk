---
actual_minutes: 19.41
---

# METR n=1 result

Predicted time: 60 minutes.
Actual time: 19.41 minutes.
Actual/predicted ratio: 0.32.

The feature measured in this experiment was the DORA metrics computation implemented in `src/dora_metrics.py`. Before implementation I predicted that the work would take 60 minutes. The measured implementation time was 19.41 minutes, giving an actual/predicted ratio of 0.32.

The prediction was recorded and receipted before implementation began. During the measured work I implemented parsing and validation of the event log, the five delivery metrics, the published edge-case rules, anomaly counts, and ground-truth fields. I then tested the implementation against the published practice fixture and compared the returned object with the expected values supplied by the course.

The implementation took less time than predicted because the specification provided precise rules and the published fixture gave immediate feedback. The estimate also included uncertainty around the six edge cases, particularly revert chains, clock skew, deployments without commits, and overlapping incidents. This result is therefore one n=1 observation rather than evidence that future work will always take approximately one third of the original estimate.
