---
lab5_triage:
  image: ghcr.io/iwonaszukala/itsm-svcdesk@sha256:3e5cc7c757c15aee9c2b7690c53cd17ecc165a29ce0019dfa55d77163b1b7063
  sarif_receipt: 402
---
<!-- ai-generated: 80% - Claude Code drafted the rows and the Bake-off from my pipeline runs, the receipted SARIF and bakeoff.json; I took the decisions (fix the root user, false-positive on the KB URL, ignore the Helm checksum) and checked every number -->
# Triage

What the gates and the reporting scanners found on my service, and what I did about each (CI-SPEC.md P-11, P-12).
The receipted SARIF (receipt #402, canary commit `d410629`) has two rules on my own code outside `lab5-canary/`, both
from Semgrep; the third row is the one finding a gate stopped on `main`. The image gate never needed an ignore:
`.trivyignore` is empty, because the Dockerfile itself was fixed (base image pinned to the 2026-11-14 digest of
`python:3.13-slim`, `apt-get upgrade`, and `pip uninstall -y pip` after installing, which removes pip's vendored
msgpack, urllib3 and `pkg_resources`). Locally and in CI, Trivy 0.74.0 reports 0 fixable HIGH or CRITICAL
vulnerabilities in the image.

| Tool | Rule | Decision | Reason |
|---|---|---|---|
| semgrep | dockerfile.security.missing-user.missing-user | fix | `Dockerfile` line 14 (in the receipted SARIF): the container ran as root. Fixed in commit `62425db`: a system user `svcdesk` (uid 10001) owns `/data`, the SQLite volume, and the image ends with `USER svcdesk`; the 12 compose tests pass as that user and the image digest above is that build. |
| semgrep | python.lang.security.audit.dynamic-urllib-use-detected.dynamic-urllib-use-detected | false-positive | `src/main.py:661`, `kb_search`: the URL is `KB_INDEX_URL` (operator configuration, `http://kb-index:8080` in compose) plus a query string built by `urlencode`; the caller controls only the encoded `q` value, never the scheme, host or path, so the `file://` read the rule warns about is not reachable from a request. |
| gitleaks | generic-api-key | ignore | `k8s/evidence.json:5314` (Lab 3 evidence) stopped the `secrets` gate on `main` run 43610599395: the value is Helm's `checksum/secret` pod annotation, a SHA-256 digest of the rendered Grafana Secret, not a credential. Ignored by fingerprint in `.gitleaksignore` with that reason above it; the gate went green on the next run. |

## Bake-off

My canary set has 10 labelled defects: 5 in code (two injections A02 and A11, two deserializations A09 and A10, one
SSRF A16), 3 credentials (C05, C06, C07) and 2 vulnerable pins (Jinja2 D03, urllib3 D08). Per tool:

- **Semgrep**: TP 6, FP 1, FN 4 - precision 0.8571, recall 0.6, F1 0.7059. It found all four code defects it has
  rules for (`shell=True`, `eval`, `yaml.load` and `pickle`) and two credentials (a generic API key and a private
key). Its one false positive is the decoy
  `app/columns.py`: an f-string `ORDER BY {column}` whose column comes from a fixed allow-list - the rule sees string
  building, not the allow-list.
- **Trivy**: TP 3, FP 0, FN 7 - precision 1.0, recall 0.3, F1 0.4615. Both pins, plus the private key in
  `signing_key.py` through its secret scanner; 20 results collapse onto those 3 defects.
- **gitleaks**: TP 2, FP 0, FN 8 - precision 1.0, recall 0.2, F1 0.3333 (C06 and C07).
- **Grype** and **OSV-Scanner**: TP 2, FP 0, FN 8 each - precision 1.0, recall 0.2, F1 0.3333; exactly Trivy's two
  pins again, in 19 and 38 results.

Which detector I would put in a gate: **Trivy (dependencies) and gitleaks stay blocking**, because a gate must not
cry wolf - both had precision 1.0 here, and each covers a class nothing else covers as well. **Semgrep is the most
useful detector** (best recall 0.6 and F1 0.71) but with precision 0.857 it would have blocked a correct, allow-listed
query; I would gate only on its high-confidence rules (`pickle`, `yaml.load`, `eval`, `shell=True`) and keep the rest
report-only, triaged in this table. Grype and OSV-Scanner add nothing over Trivy on this set (the same two defects,
many more results), so they stay as reporting second opinions, not gates.

What surprised me: gitleaks missed C05, `SMTP_PASSWORD = "Wq5!..."` in `config/mailer.py` - a plain password
assignment with no provider prefix and modest entropy - while Semgrep caught a different credential; no single
secret scanner is enough. The defects nobody found are A16, an SSRF where `requests.post` takes a customer-supplied
callback URL (no rule in `p/default` tracks a function parameter into a request), and C05: both need knowing where
the data comes from, not what the line looks like. And every recall here is an **upper bound**: these defects were
seeded to be findable, in short files, and seeded defects flatter every detector - on real code I would expect less.
