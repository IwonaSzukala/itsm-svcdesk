# ai-generated: 85% - AI drafted this one-shot OpenTelemetry capture script; I ran it against my local Ollama endpoint and reviewed the exported spans

from openai import OpenAI
from opentelemetry import trace
from opentelemetry.exporter.otlp.json.file import FileSpanExporter
from opentelemetry.instrumentation.genai.openai import OpenAIInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

provider = TracerProvider(
    resource=Resource.create({"service.name": "lab3-genai"})
)
trace.set_tracer_provider(provider)

exporter = FileSpanExporter("/work/genai/spans.json")
provider.add_span_processor(SimpleSpanProcessor(exporter))

OpenAIInstrumentor().instrument()

client = OpenAI(
    base_url="http://host.docker.internal:11434/v1",
    api_key="ollama",
)

response = client.chat.completions.create(
    model="qwen3:1.7b",
    messages=[
        {
            "role": "user",
            "content": "In one short sentence, explain what an SLO is."
        }
    ],
    max_tokens=80,
)

print("MODEL RESPONSE:")
print(response.choices[0].message.content)

provider.force_flush()
provider.shutdown()