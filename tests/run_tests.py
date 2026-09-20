import json
import os
import sys
import urllib.request
import uuid

BASE_URL = os.environ.get("SVCDESK_URL", "http://svcdesk:8080")

passed = 0
failed = 0


def request(method, path, payload=None):
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers=headers,
        method=method,
    )

    with urllib.request.urlopen(req, timeout=10) as response:
        body = response.read().decode("utf-8")
        return response.status, json.loads(body)


def check(name, condition):
    global passed, failed

    if condition:
        passed += 1
        print(f"PASS: {name}")
    else:
        failed += 1
        print(f"FAIL: {name}")


def create_ticket(impact, urgency, vip=False):
    payload = {
        "title": "Stretch test " + uuid.uuid4().hex,
        "description": "Automated Lab 1 stretch test.",
        "reporter": {
            "name": "Stretch Tester",
            "vip": vip,
        },
        "impact": impact,
        "urgency": urgency,
    }

    return request("POST", "/tickets", payload)


try:
    status, health = request("GET", "/health")
    check("health", status == 200 and health.get("status") == "ok")

    status, p1 = create_ticket(1, 1)
    check("create P1", status == 201 and p1.get("priority") == "P1")

    status, p2 = create_ticket(1, 2)
    check("create P2", status == 201 and p2.get("priority") == "P2")

    status, p3 = create_ticket(2, 2)
    check("create P3", status == 201 and p3.get("priority") == "P3")

    status, p4 = create_ticket(3, 3)
    check("create P4", status == 201 and p4.get("priority") == "P4")

    status, vip = create_ticket(3, 3, True)
    check("VIP promotion", status == 201 and vip.get("priority") == "P2")

    status, fetched = request("GET", f"/tickets/{p1['id']}")
    check("get ticket", status == 200 and fetched.get("id") == p1["id"])

    status, tickets = request("GET", "/tickets")
    check("list tickets", status == 200 and isinstance(tickets, list))

    status, ack = request("POST", f"/tickets/{p2['id']}/ack")
    check("ack ticket", status == 200 and ack.get("state") == "acknowledged")

    status, started = request("POST", f"/tickets/{p2['id']}/start")
    check("start ticket", status == 200 and started.get("state") == "in_progress")

    status, resolved = request("POST", f"/tickets/{p2['id']}/resolve")
    check("resolve ticket", status == 200 and resolved.get("state") == "resolved")

    status, sla = request("GET", f"/tickets/{p1['id']}/sla")
    check(
        "SLA endpoint",
        status == 200
        and "ack_due_at" in sla
        and "resolve_due_at" in sla
    )

except Exception as exc:
    failed += 1
    print(f"FAIL: unexpected exception: {exc}")

print(f"ITSMLAB-TESTS: passed={passed} failed={failed}")
sys.exit(0 if failed == 0 and passed >= 10 else 1)
