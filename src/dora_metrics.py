# ai-generated: 80% - AI drafted the implementation; I reviewed, tested and corrected it against METRIC-SPEC.md

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP


class MetricInputError(ValueError):
    pass


def parse_timestamp(value):
    if not isinstance(value, str):
        raise MetricInputError("invalid timestamp")

    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MetricInputError("invalid timestamp") from exc

    if parsed.tzinfo is None:
        raise MetricInputError("timestamp must include timezone")

    return parsed.astimezone(timezone.utc)


def duration_seconds(later, earlier):
    delta = later - earlier

    return (
        Decimal(delta.days * 86400 + delta.seconds)
        + Decimal(delta.microseconds) / Decimal(1_000_000)
    )


def round_seconds(value):
    return int(
        value.quantize(
            Decimal("1"),
            rounding=ROUND_HALF_UP,
        )
    )


def round_six(value):
    return float(
        value.quantize(
            Decimal("0.000001"),
            rounding=ROUND_HALF_UP,
        )
    )


def median(values):
    if not values:
        return None

    ordered = sorted(values)
    count = len(ordered)

    if count % 2:
        value = ordered[count // 2]
    else:
        value = (
            ordered[count // 2 - 1]
            + ordered[count // 2]
        ) / Decimal(2)

    return round_seconds(value)


def compute_metrics(body):
    if not isinstance(body, dict):
        raise MetricInputError(
            "request body must be an object"
        )

    window = body.get("window")
    events = body.get("events")

    if not isinstance(window, dict):
        raise MetricInputError("window is required")

    if not isinstance(events, list):
        raise MetricInputError(
            "events must be an array"
        )

    start = parse_timestamp(window.get("from"))
    end = parse_timestamp(window.get("to"))

    if end <= start:
        raise MetricInputError(
            "window.to must be after window.from"
        )

    # R-05: first event_id wins.
    unique_events = []
    seen_event_ids = set()

    for event in events:
        if not isinstance(event, dict):
            raise MetricInputError(
                "event must be an object"
            )

        event_id = event.get("event_id")

        if (
            not isinstance(event_id, str)
            or not 1 <= len(event_id) <= 64
        ):
            raise MetricInputError(
                "invalid event_id"
            )

        if event_id in seen_event_ids:
            continue

        seen_event_ids.add(event_id)
        unique_events.append(event)

    commits = {}
    deployments = {}
    incident_events = []

    for event in unique_events:
        event_type = event.get("type")
        event_at = parse_timestamp(
            event.get("at")
        )

        if event_type == "commit":
            sha = event.get("sha")
            branch = event.get("branch")
            change_id = event.get("change_id")
            reverts = event.get("reverts")

            if (
                not isinstance(sha, str)
                or sha in commits
                or not isinstance(branch, str)
            ):
                raise MetricInputError(
                    "invalid commit"
                )

            if reverts is None:
                if not isinstance(change_id, str):
                    raise MetricInputError(
                        "normal commit requires change_id"
                    )
            else:
                if (
                    not isinstance(reverts, str)
                    or change_id is not None
                ):
                    raise MetricInputError(
                        "revert commit is malformed"
                    )

            commits[sha] = {
                **event,
                "_at": event_at,
            }

        elif event_type == "deployment":
            deployment_id = event.get(
                "deployment_id"
            )
            environment = event.get(
                "environment"
            )
            outcome = event.get("outcome")
            commit_list = event.get("commits")
            unplanned = event.get("unplanned")
            caused_by = event.get("caused_by")

            if (
                not isinstance(
                    deployment_id,
                    str,
                )
                or deployment_id in deployments
                or not isinstance(
                    environment,
                    str,
                )
                or outcome
                not in ("success", "failure")
                or not isinstance(
                    commit_list,
                    list,
                )
                or not all(
                    isinstance(sha, str)
                    for sha in commit_list
                )
                or not isinstance(
                    unplanned,
                    bool,
                )
                or (
                    caused_by is not None
                    and not isinstance(
                        caused_by,
                        str,
                    )
                )
            ):
                raise MetricInputError(
                    "invalid deployment"
                )

            deployments[deployment_id] = {
                **event,
                "_at": event_at,
            }

        elif event_type == "incident":
            incident_id = event.get(
                "incident_id"
            )
            phase = event.get("phase")
            covered = event.get("deployments")

            if (
                not isinstance(
                    incident_id,
                    str,
                )
                or phase
                not in ("opened", "resolved")
                or not isinstance(
                    covered,
                    list,
                )
                or not all(
                    isinstance(item, str)
                    for item in covered
                )
            ):
                raise MetricInputError(
                    "invalid incident"
                )

            incident_events.append(
                {
                    **event,
                    "_at": event_at,
                }
            )

        else:
            raise MetricInputError(
                "invalid event type"
            )

    for commit in commits.values():
        reverted = commit["reverts"]

        if (
            reverted is not None
            and reverted not in commits
        ):
            raise MetricInputError(
                "reverts references unknown sha"
            )

    for deployment in deployments.values():
        for sha in deployment["commits"]:
            if sha not in commits:
                raise MetricInputError(
                    "deployment references unknown sha"
                )

    incidents = {}

    for event in incident_events:
        incident_id = event["incident_id"]

        incident = incidents.setdefault(
            incident_id,
            {
                "opened": None,
                "resolved": None,
                "deployments": set(),
            },
        )

        phase = event["phase"]

        if incident[phase] is not None:
            raise MetricInputError(
                "duplicate incident phase"
            )

        incident[phase] = event["_at"]

        incident["deployments"].update(
            event["deployments"]
        )

    for incident in incidents.values():
        if (
            incident["resolved"] is not None
            and incident["opened"] is None
        ):
            raise MetricInputError(
                "resolved incident was never opened"
            )

        for deployment_id in (
            incident["deployments"]
        ):
            if deployment_id not in deployments:
                raise MetricInputError(
                    "incident references unknown deployment"
                )

    for deployment in deployments.values():
        caused_by = deployment["caused_by"]

        if (
            caused_by is not None
            and caused_by not in incidents
        ):
            raise MetricInputError(
                "caused_by references unknown incident"
            )

    # R-06: resolve revert chains.
    resolved_changes = {}
    resolving = set()

    def change_for(sha):
        if sha in resolved_changes:
            return resolved_changes[sha]

        if sha in resolving:
            raise MetricInputError(
                "revert cycle"
            )

        resolving.add(sha)

        commit = commits[sha]

        if commit["reverts"] is None:
            change_id = commit["change_id"]
        else:
            change_id = change_for(
                commit["reverts"]
            )

        resolving.remove(sha)

        resolved_changes[sha] = change_id

        return change_id

    for sha in commits:
        change_for(sha)

    changes = set(
        resolved_changes.values()
    )

    # R-07: earliest commit per change.
    first_change_commit = {}

    for sha, commit in commits.items():
        change_id = resolved_changes[sha]

        if (
            change_id
            not in first_change_commit
            or commit["_at"]
            < first_change_commit[change_id]
        ):
            first_change_commit[
                change_id
            ] = commit["_at"]

    # R-01 and R-02.
    scoped_deployments = [
        deployment
        for deployment
        in deployments.values()
        if (
            deployment["environment"]
            == "production"
            and start
            <= deployment["_at"]
            < end
        )
    ]

    successful = [
        deployment
        for deployment
        in scoped_deployments
        if deployment["outcome"]
        == "success"
    ]

    failed = [
        deployment
        for deployment
        in scoped_deployments
        if deployment["outcome"]
        == "failure"
    ]

    # R-08.
    first_success_for_commit = {}

    for deployment in sorted(
        successful,
        key=lambda item: item["_at"],
    ):
        for sha in deployment["commits"]:
            if sha not in (
                first_success_for_commit
            ):
                first_success_for_commit[
                    sha
                ] = deployment["_at"]

    lead_times = []
    negative_lead_time_pairs = 0

    for (
        sha,
        deployment_at,
    ) in first_success_for_commit.items():

        seconds = duration_seconds(
            deployment_at,
            commits[sha]["_at"],
        )

        if seconds < 0:
            negative_lead_time_pairs += 1
            seconds = Decimal(0)

        lead_times.append(seconds)

    # R-09.
    commits_never_on_main = set()

    for deployment in scoped_deployments:
        for sha in deployment["commits"]:
            if commits[sha]["branch"] != "main":
                commits_never_on_main.add(
                    sha
                )

    # R-10.
    deployments_without_commits = sum(
        1
        for deployment
        in scoped_deployments
        if not deployment["commits"]
    )

    # R-12.
    recovery_times = []
    open_failures = 0

    for deployment in failed:
        candidates = []

        for (
            incident_id,
            incident,
        ) in incidents.items():

            if (
                deployment["deployment_id"]
                in incident["deployments"]
                and incident["opened"]
                is not None
            ):
                candidates.append(
                    (
                        incident["opened"],
                        incident_id,
                        incident,
                    )
                )

        if not candidates:
            open_failures += 1
            continue

        candidates.sort(
            key=lambda item: (
                item[0],
                item[1],
            )
        )

        covering_incident = (
            candidates[0][2]
        )

        if (
            covering_incident["resolved"]
            is None
        ):
            open_failures += 1
            continue

        seconds = duration_seconds(
            covering_incident["resolved"],
            deployment["_at"],
        )

        if seconds < 0:
            seconds = Decimal(0)

        recovery_times.append(seconds)

    # R-13.
    incident_intervals = []

    for (
        incident_id,
        incident,
    ) in incidents.items():

        if incident["opened"] is None:
            continue

        interval_end = (
            incident["resolved"]
            if incident["resolved"]
            is not None
            else end
        )

        incident_intervals.append(
            (
                incident_id,
                incident["opened"],
                interval_end,
            )
        )

    overlapping_incident_pairs = 0

    for left_index in range(
        len(incident_intervals)
    ):
        for right_index in range(
            left_index + 1,
            len(incident_intervals),
        ):
            (
                _,
                left_start,
                left_end,
            ) = incident_intervals[
                left_index
            ]

            (
                _,
                right_start,
                right_end,
            ) = incident_intervals[
                right_index
            ]

            if (
                left_start < right_end
                and right_start < left_end
            ):
                overlapping_incident_pairs += 1

    deployment_count = len(
        scoped_deployments
    )

    rework_count = sum(
        1
        for deployment
        in scoped_deployments
        if (
            deployment["unplanned"]
            is True
            and deployment["caused_by"]
            is not None
        )
    )

    window_seconds = duration_seconds(
        end,
        start,
    )

    window_days = (
        window_seconds
        / Decimal(86400)
    )

    deployment_frequency = round_six(
        Decimal(deployment_count)
        / window_days
    )

    change_fail_rate = (
        round_six(
            Decimal(len(failed))
            / Decimal(deployment_count)
        )
        if deployment_count
        else None
    )

    deployment_rework_rate = (
        round_six(
            Decimal(rework_count)
            / Decimal(deployment_count)
        )
        if deployment_count
        else None
    )

    # R-16 and R-17.
    first_success_for_change = {}

    for deployment in sorted(
        successful,
        key=lambda item: item["_at"],
    ):
        for sha in deployment["commits"]:
            change_id = (
                resolved_changes[sha]
            )

            if (
                change_id
                not in first_success_for_change
            ):
                first_success_for_change[
                    change_id
                ] = deployment["_at"]

    true_change_lead_times = []

    for (
        change_id,
        deployment_at,
    ) in first_success_for_change.items():

        seconds = duration_seconds(
            deployment_at,
            first_change_commit[
                change_id
            ],
        )

        if seconds < 0:
            seconds = Decimal(0)

        true_change_lead_times.append(
            seconds
        )

    return {
        "spec_version": "1.0.0",
        "window": {
            "from": window["from"],
            "to": window["to"],
        },
        "deployment_frequency_per_day":
            deployment_frequency,
        "change_lead_time_seconds_p50":
            median(lead_times),
        "failed_deployment_recovery_time_seconds_p50":
            median(recovery_times),
        "change_fail_rate":
            change_fail_rate,
        "deployment_rework_rate":
            deployment_rework_rate,
        "counts": {
            "deployments":
                deployment_count,
            "successful_deployments":
                len(successful),
            "failed_deployments":
                len(failed),
            "recovered_failures":
                len(recovery_times),
            "open_failures":
                open_failures,
            "rework_deployments":
                rework_count,
            "lead_time_pairs":
                len(lead_times),
            "changes":
                len(changes),
        },
        "anomalies": {
            "negative_lead_time_pairs":
                negative_lead_time_pairs,
            "deployments_without_commits":
                deployments_without_commits,
            "commits_never_on_main":
                len(commits_never_on_main),
            "revert_chains_collapsed":
                sum(
                    1
                    for commit
                    in commits.values()
                    if commit["reverts"]
                    is not None
                ),
            "overlapping_incident_pairs":
                overlapping_incident_pairs,
        },
        "ground_truth": {
            "changes_delivered":
                len(
                    first_success_for_change
                ),
            "true_change_lead_time_seconds_p50":
                median(
                    true_change_lead_times
                ),
        },
    }