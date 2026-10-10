<!-- ai-generated: 80% - AI helped draft the explanation from my measured client and server p99 values; I reviewed the measurements and interpretation -->

# Client-server latency gap

I measured GET /kb/search through Toxiproxy with a downstream latency toxic configured for 100 ms latency and 10 ms jitter. The client-side p99 reported by the load generator was 0.2780 seconds, while the server-side p99 calculated from svcdesk's own request-duration histogram over the same run was 0.1691 seconds. The measured client-server gap is therefore 0.2780 - 0.1691 = 0.1089 seconds, or 108.9 ms.

The difference exists because svcdesk measures how long it spends processing the request, including its call to kb-index, but the downstream Toxiproxy delay is introduced after svcdesk has produced the response. That extra network-path delay is visible to the client but is outside the server's request-duration observation. The measured gap is close to the configured 100 ms toxic, with the remaining variation explained by the configured 10 ms jitter and normal scheduling and network timing variation.