---
svcdesk_decisions:
  C1: wallclock      # wallclock | business
  C2: immutable      # reopen | immutable
  C3: vip            # matrix | vip
---
<!-- ai-generated: 100% - generated with AI and reviewed by the student -->

# Decisions

<!--
How to fill this in (delete this comment when you are done):
- The three values in the front matter must be the ones your RUNNING service exhibits. The checker probes the
  service (checks 2.41, 2.35, 2.46) and compares them with this file (L1-CORE-4).
- Keep the three headings starting with "## C1", "## C2", "## C3" and the five bold labels in each section. Write
  at least 20 characters after every label; the lecturer reads this document, so write what you would say to
  the service owner, not the minimum.
- "Service owner": the role (never a person's name) who would sign this decision off, and why it is theirs.
- "Customer outcome": what the reporter or the organisation gets from this choice, in one or two sentences.
- Update the ai-generated line above to say how much of this text an AI wrote and how.
-->

## C1 - SLA clock for P1

## C1 - SLA clock for P1

**Decision:** P1 tickets use the wall-clock SLA.

**Rejected alternative:** P1 tickets using the business-hours clock was rejected.

**Reason:** P1 represents the most urgent incidents, so its acknowledgement and resolution deadlines should continue outside normal business hours.

**Service owner:** The Service Desk product owner should approve this because they are responsible for the SLA policy and escalation expectations.

**Customer outcome:** Critical incidents remain time-sensitive during evenings and weekends, giving users a predictable response target.

## C2 - Closed tickets and reopening

**Decision:** Closed tickets are immutable and cannot be reopened.

**Rejected alternative:** Allowing closed tickets to be reopened within seven days was rejected.

**Reason:** A closed ticket represents completed work and should remain unchanged so that reporting and audit history stay consistent.

**Service owner:** The Service Desk product owner should approve this because they define the ticket lifecycle and reporting rules.

**Customer outcome:** Users get a clear history of completed incidents, while recurring problems are recorded as new related tickets.

## C3 - VIP reporters and the priority matrix

**Decision:** VIP reporters can raise a calculated P3 or P4 priority to P2.

**Rejected alternative:** Using only the impact and urgency matrix for VIP reporters was rejected.

**Reason:** VIP incidents should receive increased visibility while still preserving P1 for the highest-impact and highest-urgency incidents.

**Service owner:** The Service Desk product owner should approve this because they define priority and escalation policy.

**Customer outcome:** VIP issues receive faster attention without replacing the normal P1 classification for major incidents.
