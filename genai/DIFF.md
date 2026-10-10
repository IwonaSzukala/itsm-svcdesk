---
lab3_genai_diff:
  instrumentation: "opentelemetry-instrumentation-genai-openai 1.2b0; opentelemetry-sdk 1.45.0"
  spec_ref: "semantic-conventions-genai@e57c543b4889619eb2a05702471937db5119165d"
  attributes:
    - {name: gen_ai.operation.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.provider.name, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.request.max_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.finish_reasons, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.model, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.response.id, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.input_tokens, emitted: true, in_spec: true, stability: development}
    - {name: gen_ai.usage.output_tokens, emitted: true, in_spec: true, stability: development}
---
<!-- ai-generated: 80% - AI helped compare my captured OpenTelemetry span attributes with the pinned GenAI semantic-conventions registry; I reviewed the emitted attribute set -->

# What the library emits, against the spec

I captured one instrumented OpenAI-compatible chat completion using `opentelemetry-instrumentation-genai-openai` 1.2b0 against a local Ollama `qwen3:1.7b` model. The OpenTelemetry SDK version was 1.45.0.

The span emitted nine `gen_ai.*` attributes. All nine are defined by the pinned `semantic-conventions-genai` reference used for this comparison, and all nine are marked `development` there.

The instrumentation emitted the core operation identity fields `gen_ai.operation.name`, `gen_ai.provider.name`, and `gen_ai.request.model`. It also recorded the configured request limit in `gen_ai.request.max_tokens`.

For the response it emitted `gen_ai.response.id`, `gen_ai.response.model`, and `gen_ai.response.finish_reasons`. The captured finish reason was `length` because the test call reached the configured maximum of 80 output tokens.

It also emitted both token-accounting attributes: `gen_ai.usage.input_tokens` and `gen_ai.usage.output_tokens`. In this capture their values were 22 and 80 respectively.

For a dashboard, these attributes are useful for grouping latency and usage by operation, provider and model, and for correlating unusually expensive calls with token counts. Because the compared attributes are still marked `development`, a production dashboard should not assume their names and semantics will remain unchanged across future instrumentation or semantic-convention upgrades.