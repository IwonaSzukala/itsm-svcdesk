---
lab4_comms:
  awareness: 2026-10-12T07:09:19Z        # NIS2: the detecting alert's firing start (= detection)
  detection: 2026-10-12T07:09:19Z        # KSC: the detecting alert ShopCheckoutErrors began firing
  classification: 2026-10-12T07:10:07Z   # DORA: the P1 ticket's acknowledgement
  nis2:
    early_warning_due: 2026-10-13T07:09:19Z      # awareness + 24 h
    notification_due: 2026-10-15T07:09:19Z       # awareness + 72 h
    notification_sent: 2026-10-14T09:00:00Z
    final_report_due: 2026-11-14T09:00:00Z       # one calendar month after notification_sent
  ksc:
    early_warning_due: 2026-10-13T07:09:19Z      # detection + 24 h
    notification_due: 2026-10-15T07:09:19Z       # detection + 72 h
    notification_sent: 2026-10-14T09:00:00Z
    final_report_due: 2026-11-14T09:00:00Z       # one calendar month after notification_sent
  dora:
    initial_due: 2026-10-12T11:10:07Z            # classification + 4 h; earlier than awareness + 24 h
    initial_sent: 2026-10-12T10:30:00Z
    intermediate_due: 2026-10-15T10:30:00Z       # initial_sent + 72 h
    intermediate_sent: 2026-10-15T09:00:00Z
    final_due: 2026-11-15T09:00:00Z              # one calendar month after intermediate_sent
  log:
    - {at: 2026-10-12T10:30:00Z, to: the financial supervisor (KNF), what: DORA initial notification of a major ICT-related incident}
    - {at: 2026-10-12T15:00:00Z, to: the CSIRT, what: NIS2 and KSC early warning}
    - {at: 2026-10-14T09:00:00Z, to: the CSIRT, what: NIS2 and KSC incident notification}
    - {at: 2026-10-15T09:00:00Z, to: the financial supervisor (KNF), what: DORA intermediate report}
---
<!-- ai-generated: 80% - Claude Code computed the deadlines and drafted the prose from my chosen instants (detection, awareness = detection, classification = acknowledgement); I reviewed the arithmetic with the course checker. -->

# Communications log: the regulators' clocks

The shop is treated as an entity to which NIS2, the Polish KSC act and DORA all apply, and the incident of
2026-10-12 (postmortem in `postmortem.md`, ticket `1224ad8d-06a8-4ae3-865a-da2015a4ddb5`) as significant under the
first two and major under the third. Every instant is UTC.

## The three instants you defend

**Detection (KSC) - 2026-10-12T07:09:19Z.** KSC counts "od momentu jego wykrycia", from the moment of detection. The
earliest moment at which our systems detected the incident is the start of the firing run of the detecting alert,
`ShopCheckoutErrors` (P1), which `itsmlab incident 4` recomputes from the snapshot. Before that instant the fault
existed (onset 07:05:45Z) but nothing in our tooling had recognised it; the onset is visible only in hindsight, from
the injector's series, so it cannot be the moment of detection.

**Awareness (NIS2) - 2026-10-12T07:09:19Z, the same instant.** NIS2 counts from "becoming aware" of a significant
incident. The P1 alert pages the on-call directly, and its rule is a symptom of customer impact - checkout orders
failing - so the organisation operationally becomes aware of an incident that affects its service at the moment the
page is raised. Choosing a later moment (the acknowledgement, or the end of triage) would let the clock depend on how
quickly a human reacts, which is exactly what the regulation wants to avoid. Awareness therefore equals detection.

**Classification (DORA) - 2026-10-12T07:10:07Z, the acknowledgement.** DORA's clock for the initial notification
starts when the incident is classified as major. The acknowledgement of the P1 ticket is the first durable,
server-stamped moment at which the on-call accepted the incident at the highest priority (impact 1, urgency 1) and
took ownership of it; P1 in our service is the priority reserved for incidents that halt a critical business
function, which is how we map DORA's "major". Because the classification falls within 24 hours of awareness, the
initial deadline is the earlier of classification + 4 h (11:10:07Z) and awareness + 24 h (07:09:19Z next day):
11:10:07Z on 2026-10-12.

## The log

| when (UTC) | to | what | clock it answers |
|---|---|---|---|
| 2026-10-12T10:30:00Z | the financial supervisor (KNF) | DORA initial notification | due 2026-10-12T11:10:07Z |
| 2026-10-12T15:00:00Z | the CSIRT | NIS2 and KSC early warning | due 2026-10-13T07:09:19Z |
| 2026-10-14T09:00:00Z | the CSIRT | NIS2 and KSC incident notification | due 2026-10-15T07:09:19Z |
| 2026-10-15T09:00:00Z | the financial supervisor (KNF) | DORA intermediate report | due 2026-10-15T10:30:00Z |

The NIS2 and KSC final reports are due one calendar month after the notification, on 2026-11-14T09:00:00Z, and
DORA's final report one calendar month after the intermediate report, on 2026-11-15T09:00:00Z. Every report is sent
before its deadline; the DORA initial notification goes out 40 minutes early, once the impact on orders and the
rollback of the flags (07:13:20Z) are known.
