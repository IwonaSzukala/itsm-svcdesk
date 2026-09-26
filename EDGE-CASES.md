---
lab2_edge_cases:
  E1: {rule: R-08, count: 3}
  E2: {rule: R-06, count: 2}
  E3: {rule: R-09, count: 4}
  E4: {rule: R-10, count: 4}
  E5: {rule: R-12, count: 1}
  E6: {rule: R-13, count: 11}
---
<!-- ai-generated: 80% - AI drafted the explanations; I reviewed them against METRIC-SPEC.md and my service output -->

# Edge cases in the practice event log

## E1 - clock skew produces a negative lead time

- What the log contains: Three deployment and commit pairs have commit timestamps later than the deployment timestamps because the clocks disagree.
- What a default definition would have done: A simple implementation might discard the negative values or keep them as negative durations, which would distort the lead-time metric.
- Why the rule is defensible: R-08 clamps these durations to zero but still counts the pairs, preserving the delivery evidence without allowing clock skew to create impossible negative lead times.

## E2 - a revert of a revert

- What the log contains: Two commits are revert commits, including a revert that targets another revert and therefore belongs to the original change transitively.
- What a default definition would have done: A naive implementation could count each revert as a separate change and artificially increase the number of distinct changes delivered.
- Why the rule is defensible: R-06 resolves revert chains back to the original change, so reverts do not invent new units of work that were never separate changes.

## E3 - a hotfix that never touched `main`

- What the log contains: Four distinct commit shas reaching production are from branches other than `main`, including hotfix-style delivery directly to production.
- What a default definition would have done: A definition filtering only commits from `main` would ignore real production work and under-report delivered changes and lead-time pairs.
- Why the rule is defensible: R-09 treats branch names as irrelevant because reaching production is the important fact, regardless of which branch carried the commit.

## E4 - a deployment with zero linked commits

- What the log contains: Four production deployments inside the observation window contain an empty `commits` array but are still real deployment events.
- What a default definition would have done: A naive implementation might remove these deployments entirely because no commit can be paired with them for lead-time calculation.
- Why the rule is defensible: R-10 excludes them only from lead-time pairs while keeping them in deployment frequency and the denominators of the failure and rework rates.

## E5 - a deployment that failed and never recovered

- What the log contains: One failed production deployment has no usable resolved covering incident, so there is no observed recovery instant for that failure.
- What a default definition would have done: A simplistic metric might invent a recovery at the end of the window or silently omit the failed deployment from failure accounting.
- Why the rule is defensible: R-12 records it as an open failure and excludes it only from the recovery-time median because a recovery duration cannot be measured without a real recovery event.

## E6 - overlapping incidents

- What the log contains: The incident intervals create eleven unordered overlapping incident pairs when their opened and resolved intervals are compared.
- What a default definition would have done: A default approach might merge overlapping incidents or sum their durations, losing the relationship between individual failed deployments and their recovery.
- Why the rule is defensible: R-13 computes recovery per failed deployment and keeps incidents separate, so overlapping operational events do not become one artificial incident.

## Gaming demonstration

I improved `deployment_frequency_per_day` using R-11. I added thirteen successful production deployment events with no linked commits, while moving two existing successful deployments beyond the observation window. The reported deployment frequency increased from 2.0 to 2.52381 deployments per day, even though delivery of the work that already existed became worse: the number of base changes delivered fell from 65 to 57.

This demonstrates how a team could optimize the dashboard rather than delivery. If management rewarded a high deployment count, teams would have an incentive to create more operationally meaningless deployment events or split activity into additional deployments even when that did not deliver more useful work. The people or teams measured by deployment frequency would receive the apparent reward, while users and stakeholders would experience slower or reduced delivery of the original work.