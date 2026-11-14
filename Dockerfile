# python:3.13-slim as of 2026-11-14, pinned by digest so the image gate sees a known base
FROM python:3.13-slim@sha256:e48f59cdba69a3cbd9ed2cf0f348d90d45a8d350d98134cf1070bc106ee9ed90

RUN apt-get update && apt-get upgrade -y && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# pip only installs; svcdesk never calls it at run time, and its vendored packages carry fixable CVEs
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt && pip uninstall -y pip

COPY src ./src

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8080"]
