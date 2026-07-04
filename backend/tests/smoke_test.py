"""
Live smoke tests — hit the real deployed Cloud Run backend.
Run: python3 tests/smoke_test.py
NOT mocked. Requires live backend + valid API keys.
"""
import sys, json, urllib.request

BASE = "https://citizens-india-backend-564262191703.us-central1.run.app"
results = []

def assert_eq(a, b): assert a == b, f"expected {b!r}, got {a!r}"
def assert_in(k, d): assert k in d, f"{k!r} not in response"
def assert_is(t, v): assert v == t, f"expected {t}, got {v}"

def get(path):
    with urllib.request.urlopen(f"{BASE}{path}", timeout=15) as r:
        return json.loads(r.read())

def post(path, data):
    body = json.dumps(data).encode()
    req = urllib.request.Request(f"{BASE}{path}", data=body,
          headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read())

def check(name, fn):
    try:
        fn()
        print(f"  \033[92m✓\033[0m {name}")
        results.append((name, True, None))
    except Exception as e:
        print(f"  \033[91m✗\033[0m {name}: {e}")
        results.append((name, False, str(e)))

print(f"\n🔍 Smoke testing: {BASE}\n")

check("GET /health returns ok",
    lambda: assert_eq(get("/health")["status"], "ok"))

check("POST /submissions/text — real Gemini AI call succeeds", lambda: [
    assert_in("theme", (r := post("/submissions/text", {
        "text": "Smoke test: road broken near village hospital.",
        "language": "en", "constituency": "SmokeTest"}))),
    assert_in("urgency", r),
    assert_in(r["urgency"], ["High", "Medium", "Low"]),
])

check("GET /analytics/summary returns total_submissions",
    lambda: assert_in("total_submissions", get("/analytics/summary")))

check("GET /analytics/themes returns list",
    lambda: assert_is(list, type(get("/analytics/themes"))))

check("GET /docs returns 200",
    lambda: assert_eq(
        urllib.request.urlopen(f"{BASE}/docs", timeout=10).status, 200))

check("GET /submissions/list returns list",
    lambda: assert_is(list, type(get("/submissions/list"))))

print(f"\n{'─'*44}")
passed = sum(1 for _, ok, _ in results if ok)
total  = len(results)
status = "✅" if passed == total else "❌"
print(f"  {status}  {passed}/{total} smoke tests passed against live Cloud Run")
if passed < total:
    print("\n  Failures:")
    for name, ok, err in results:
        if not ok:
            print(f"    ✗ {name}\n      {err}")
sys.exit(0 if passed == total else 1)
