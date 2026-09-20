# Lab 1 convergence report

The implemented svcdesk service was compared with the published requirements and the API contract.

R-02 is satisfied by the /health endpoint, which returns the required service status and allows monitoring to determine whether svcdesk is available.

R-04 is implemented through the impact and urgency priority matrix. Priority is calculated by the service instead of being selected by the API client.

R-06 is implemented according to decision C3 = vip. A VIP ticket whose matrix result would be P3 or P4 is promoted to P2, while P1 and P2 remain unchanged.

R-09 and R-10 conflict over reopening closed tickets. The implementation follows decision C2 = immutable. A resolved ticket can be reopened within the permitted window, while a closed ticket remains immutable.

R-13 and R-14 conflict over the SLA clock for P1 tickets. The implementation follows decision C1 = wallclock. P1 uses wall-clock targets while P2, P3 and P4 use the business-hours clock.

The implementation was checked against the published conformance suite. The observed decisions are C1=wallclock, C2=immutable and C3=vip, matching DECISIONS.md.
