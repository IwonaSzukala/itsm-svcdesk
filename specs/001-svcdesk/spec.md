<!-- ai-generated: 50% - AI helped structure and phrase parts of the specification; the student reviewed and revised the content -->

# svcdesk specification

The svcdesk service is an HTTP API for managing service desk tickets.

Users can create tickets with a title, reporter, impact and urgency. The service assigns each ticket a unique id, state and priority.

Tickets move through these states: new, acknowledged, in_progress, resolved and closed. Invalid transitions return an error.

The service calculates SLA acknowledgement and resolution deadlines. P2, P3 and P4 use business hours. The behaviour of P1 depends on decision C1.

Reopening closed tickets depends on decision C2. VIP priority handling depends on decision C3. These decisions must match DECISIONS.md.

The service exposes GET /health and ticket endpoints defined in API.md. It runs as a Docker Compose service named svcdesk on port 8080.