<!-- ai-generated: 70% - Claude Code drafted this comparison from my two scored ledgers and the queries I ran on recording lab4-rec-3; I checked every number against the ledgers. -->
# Two AI investigators on recording lab4-rec-3

| | first investigator (`ai-rca-eval.json`) | second investigator (`ai-rca-eval-2.json`) |
|---|---|---|
| agent | course agent loop `agent.py` (recorded transcript) | course agent loop `agent.py`, run by me |
| model | `qwen3:4b-instruct` (local, Ollama) | `gemini-3.5-flash-lite` (Google AI Studio) |
| MCP server | `prom_mcp.py (mcp 2.2.0)` | `prom_mcp.py (mcp 2.2.0)`, pointed at the served recording |
| question | "Checkout errors paged at 07:09:19Z ... What is the cause?" | the same question; the transcript also holds runs that asked to look at errors, latency and resources of every service, after the first run stated only two hypotheses |
| hypotheses | 4: 1 correct, 1 partially correct, 2 hallucinated | 5: 3 correct, 1 partially correct, 1 hallucinated |

`ai-rca/second/transcript.md` holds five runs of the same model, as the agent appended them: runs 1 and 5 completed
and are quoted (G1-G2 from run 1, G3-G5 from run 5); runs 2 to 4 were cut short by the provider's rate limit (HTTP
429) and contain tool calls but no model text, so nothing is quoted from them.

## Where they agreed

Both investigators found the one fault that is visible in checkout's own spans: product-catalog failing GetProduct.
qwen's H2 ("downstream failures in `oteldemo.ProductCatalogService/GetProduct`") and Gemini's G2 and G4 make the same
claim, and the same kind of query confirms all three: product-catalog's GetProduct SERVER spans failed at 0.149/s at
07:11:00Z and checkout's failed GetProduct client calls (0.0082/s) match its failed orders one for one, with nothing
on the baseline at 07:00:45Z. Both also correctly placed the visible damage in checkout (qwen's H1, Gemini's G1).

## Where they parted

- **Time.** qwen read a raw counter value of 2 as "a consistent count of 2 erroneous calls from 07:00Z", which is why
  H1 is only partially correct: the error series appears after the 07:05:45Z onset. Gemini queried `rate(...[5m])` at
  07:09:19Z and at 07:00:00Z and so saw that the errors were new - it compared incident and baseline, qwen did not.
- **Breadth.** Gemini named the frontend's failures too (G1, frontend errors 0.29/s at 07:11), qwen stayed on checkout.
- **Invented causes.** Each invented one cause it never queried. qwen guessed payment from general knowledge (H3,
  "payment failures commonly cause user checkout errors"): payment's error rate was 0. qwen also proposed high load
  or a resource bottleneck (H4): load fell slightly (15.79/s vs 16.11/s) and only 4 services had errors. Gemini blamed
  the `astronomy-db` database (G3's mechanism, G5): product-catalog's astronomy-db spans kept a 1.98 ms p99 and no
  errors. Its second run used `[1m]` windows, which return nothing on one-sample-a-minute span metrics, and it filled
  the gap with a guess.

## What neither found

Neither investigator found the two other seeded faults, which my own investigation identified from runtime metrics:
ad's JVM spending 0.115 s/s in garbage collection with p95 780 ms (`adManualGc`), and recommendation's product-catalog
call ratio falling from 1.0 to about 0.5 with growing memory (`recommendationCacheFailure`). Both are invisible in
checkout's error counters, which is where both agents started - partly because `alerts_at` showed them only the
checkout and per-service error alerts, so neither went beyond what the alerts already said about latency or memory.
Gemini listed the container, CPU and memory metrics but never queried them per service.

## Which was more useful

Gemini was more useful: three of its five claims are correct and the fourth has the right component, against one
correct claim of four for qwen, and its queries used real rate windows and a baseline comparison. Its one
hallucination (astronomy-db) is specific and cheap to refute with one query. qwen's two hallucinations came from not
looking at the data at all. Neither replaced the human step that mattered most - checking runtime signals of the
services the alerts did not mention - so the identified flags in the postmortem rest on my queries, not on either agent.
