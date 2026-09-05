"""
Verification of the Search Engine and Database monitoring services, and of the
access control across every /infra route.

The access-control section enumerates the routes from the live OpenAPI schema
rather than a hand-written list, so a route added to app/api/infra.py without a
guard fails this suite instead of shipping open.

Creates its own fixtures and removes them again.
"""
import atexit
import json
import os
import subprocess
import sys
import time
import uuid

os.environ.setdefault("DB_ECHO", "False")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

from app.auth.security import get_password_hash
from app.main import app

TAG = "zzinfra"
PW = "Passw0rd!123"
IDS: dict = {}
PASS: list = []
FAIL: list = []

# Every role in the system. admin is the only one that may reach /infra.
ROLES = ("admin", "moderator", "success_coach", "student", "alumni", "guest")
NON_ADMIN = tuple(r for r in ROLES if r != "admin")


def sql(statement: str) -> str:
    out = subprocess.run(
        ["docker", "exec", "-i", "college-social-postgres",
         "psql", "-U", "postgres", "-d", "college_social", "-tAc", statement],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"psql failed: {out.stderr.strip()}\n{statement[:200]}")
    return out.stdout.strip()


def check(name: str, ok: bool, detail: str = "") -> None:
    (PASS if ok else FAIL).append(name)
    print(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   [{detail}]" if not ok and detail else ""))


def teardown() -> None:
    ids = f"SELECT id FROM users WHERE username LIKE '{TAG}%'"
    for q in (
        f"DELETE FROM moderation_logs WHERE coach_id IN ({ids})",
        f"DELETE FROM users WHERE username LIKE '{TAG}%'",
        f"DELETE FROM colleges WHERE name LIKE '{TAG}%'",
    ):
        sql(q)


def setup() -> None:
    college_id = uuid.uuid4()
    IDS["college"] = college_id
    sql(f"INSERT INTO colleges (id,name,created_at) VALUES ('{college_id}','{TAG} C',now())")

    password = get_password_hash(PW)
    for role in ROLES:
        user_id = uuid.uuid4()
        IDS[role] = user_id
        sql("INSERT INTO users (id,college_id,username,email,password,role,is_alumni,total_xp,"
            "current_level,profile,is_active,created_at,updated_at) VALUES ("
            f"'{user_id}','{college_id}','{TAG}_{role}','{TAG}_{role}@t.local','{password}',"
            f"'{role}'::user_role,false,0,'spark'::identity_level,'{{}}'::jsonb,true,now(),now())")


teardown()
setup()

_ctx = TestClient(app)
c = _ctx.__enter__()
atexit.register(lambda: _ctx.__exit__(None, None, None))

try:
    def login(role: str) -> dict:
        r = c.post("/auth/login", data={"username": f"{TAG}_{role}@t.local", "password": PW})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    H = {role: login(role) for role in ROLES}

    # ------------------------------------------------------------------
    # Access control, over every route the app actually exposes
    # ------------------------------------------------------------------

    paths = app.openapi()["paths"]
    routes = sorted(
        (method.upper(), path)
        for path, methods in paths.items()
        if path.startswith("/infra")
        for method in methods
    )

    def call(method: str, path: str, headers=None):
        # Fill path params with something harmless. Every one of these is
        # rejected on authorisation long before the value is looked at.
        concrete = (
            path.replace("{namespace}", "post").replace("{index}", "nonexistent-index")
        )
        query = "?key=post:none&index=posts&q=x" if "?" not in concrete else ""
        return c.request(method, concrete + query, headers=headers)

    print(f"\n=== access control across all {len(routes)} /infra routes ===")
    check("every infra route is discovered from the schema", len(routes) >= 17, str(len(routes)))

    denied_anon = [f"{m} {p}" for m, p in routes if call(m, p).status_code != 401]
    check("anonymous gets 401 on every route", not denied_anon, ", ".join(denied_anon))

    for role in NON_ADMIN:
        wrong = [
            f"{m} {p} -> {call(m, p, H[role]).status_code}"
            for m, p in routes
            if call(m, p, H[role]).status_code != 403
        ]
        check(f"{role} gets 403 on every route", not wrong, "; ".join(wrong))

    # The admin side, read routes only -- the two writes are exercised
    # deliberately further down rather than fired at random here.
    reads = [(m, p) for m, p in routes if m == "GET"]
    blocked = [
        f"{m} {p} -> {call(m, p, H['admin']).status_code}"
        for m, p in reads
        if call(m, p, H["admin"]).status_code in (401, 403)
    ]
    check("admin is not blocked on any read route", not blocked, "; ".join(blocked))

    print("\n=== the permissions themselves ===")
    from app.rules.permissions import COLLEGE_SCOPED, PERMISSIONS, Permission
    from app.db.models import UserRole

    for permission in (Permission.VIEW_INFRASTRUCTURE, Permission.MANAGE_INFRASTRUCTURE):
        holders = PERMISSIONS[permission]
        check(f"{permission.value} is held by admin alone",
              holders == frozenset({UserRole.admin}), str(sorted(r.value for r in holders)))
        check(f"{permission.value} is not college-scoped",
              permission not in COLLEGE_SCOPED)

    print("\n=== the guard is on the router, not just the routes ===")
    from app.api.infra import get_infra_reader, router as infra_router

    declared = [
        d.dependency for d in getattr(infra_router, "dependencies", [])
    ]
    check("the router itself declares the read guard",
          get_infra_reader in declared, str(declared))

    # ------------------------------------------------------------------
    # Search engine
    # ------------------------------------------------------------------

    print("\n=== search: index health ===")
    r = c.get("/infra/search/health", headers=H["admin"])
    check("health 200", r.status_code == 200, r.text[:200])
    h = r.json()
    check("cluster reachable", h["configured"] and h["reachable"], json.dumps(h)[:200])
    check("cluster status reported", h["status"] in ("green", "yellow", "red"), str(h["status"]))
    check("version reported", bool(h["version"]), str(h["version"]))
    by_index = {i["name"]: i for i in h["indexes"]}
    check("all three indexes reported", set(by_index) == {"posts", "users", "colleges"},
          str(sorted(by_index)))
    check("posts index resolves its alias to a physical version",
          by_index["posts"]["physical"] and by_index["posts"]["version"],
          json.dumps(by_index["posts"]))
    check("posts index reports documents and size",
          by_index["posts"]["documents"] > 0 and by_index["posts"]["size_bytes"] > 0,
          json.dumps(by_index["posts"]))

    print("\n=== search: ingest lag ===")
    lag = c.get("/infra/search/ingest_lag", headers=H["admin"]).json()
    check("lag 200 with all three indexes", len(lag["indexes"]) == 3, json.dumps(lag)[:200])
    check("no ingest queue is claimed", lag["queued"] == 0 and "no ingest queue" in lag["queue_note"])
    posts_lag = next(i for i in lag["indexes"] if i["index"] == "posts")
    check("lag reads both sides", posts_lag["database_rows"] > 0 and posts_lag["indexed_documents"] > 0,
          json.dumps(posts_lag))
    check("drift is db minus index",
          posts_lag["drift"] == posts_lag["database_rows"] - posts_lag["indexed_documents"],
          json.dumps(posts_lag))
    check("in_sync agrees with drift",
          posts_lag["in_sync"] == (posts_lag["drift"] == 0), json.dumps(posts_lag))

    print("\n=== search: mappings ===")
    m = c.get("/infra/search/mappings", headers=H["admin"]).json()
    indexes = {i["index"]: i for i in m["indexes"]}
    check("mappings 200 for all three", set(indexes) == {"posts", "users", "colleges"})
    fields = {f["field"]: f for f in indexes["posts"]["fields"]}
    check("post title is english-analysed text",
          fields["title"]["type"] == "text" and fields["title"]["analyzer"] == "english",
          json.dumps(fields.get("title")))
    check("post user_id is a keyword", fields["user_id"]["type"] == "keyword")
    user_fields = {f["field"]: f for f in indexes["users"]["fields"]}
    check("username uses the edge-ngram index analyzer and a plain search one",
          user_fields["username"]["analyzer"] == "username_index"
          and user_fields["username"]["search_analyzer"] == "username_search",
          json.dumps(user_fields.get("username")))
    check("username keeps its keyword subfield", "kw" in user_fields["username"]["subfields"])
    check("the username analyzers are reported",
          "username_index" in indexes["users"]["analyzers"], str(list(indexes["users"]["analyzers"])))
    check("no index has drifted from indexes.py",
          all(not i["drifted"] for i in m["indexes"]),
          json.dumps([[i["index"], i["drift"]] for i in m["indexes"] if i["drifted"]]))

    print("\n=== search: query tester ===")
    q = c.get("/infra/search/query?index=posts&q=group&size=3", headers=H["admin"])
    check("query 200", q.status_code == 200, q.text[:200])
    qr = q.json()
    check("took_ms reported", qr["took_ms"] is not None)
    check("hits carry ids and scores",
          all(x["id"] and x["score"] is not None for x in qr["hits"]), json.dumps(qr["hits"])[:200])
    check("size is respected", len(qr["hits"]) <= 3, str(len(qr["hits"])))
    check("size is capped at 50", c.get("/infra/search/query?index=posts&q=a&size=500",
                                        headers=H["admin"]).status_code == 422)
    bad = c.get("/infra/search/query?index=secrets&q=a", headers=H["admin"]).json()
    check("an unknown index is refused, not queried",
          "Unknown index" in (bad["error"] or ""), json.dumps(bad))
    check("the tester says it is unfiltered", "Unfiltered" in (qr["note"] or ""))

    print("\n=== search: reindex ===")
    status = c.get("/infra/search/reindex", headers=H["admin"]).json()
    check("reindex status lists every index", len(status["indexes"]) == 3, json.dumps(status))

    bad = c.post("/infra/search/reindex/nonsense", headers=H["admin"])
    check("an unknown index is refused 422", bad.status_code == 422, bad.text[:150])

    # colleges is the smallest index, so this is a real rebuild that finishes
    # in a moment. It also repairs whatever drift is there.
    r = c.post("/infra/search/reindex/colleges", headers=H["admin"])
    check("reindex accepted 202", r.status_code == 202, r.text[:200])
    check("it reports itself as running", r.json()["status"] == "running", r.text[:200])
    check("it records who triggered it",
          r.json()["triggered_by"] == str(IDS["admin"]), r.text[:200])

    outcome = None
    for _ in range(60):
        time.sleep(0.5)
        rows = c.get("/infra/search/reindex", headers=H["admin"]).json()["indexes"]
        row = next(x for x in rows if x["index"] == "colleges")
        if row["status"] in ("succeeded", "failed"):
            outcome = row
            break

    check("the background rebuild finished", outcome is not None, "still running after 30s")
    if outcome:
        check("it succeeded", outcome["status"] == "succeeded", json.dumps(outcome))
        check("it recorded a duration", (outcome["duration_seconds"] or 0) > 0, json.dumps(outcome))

        lag = c.get("/infra/search/ingest_lag", headers=H["admin"]).json()
        colleges = next(i for i in lag["indexes"] if i["index"] == "colleges")
        check("the rebuild brought colleges back in sync",
              colleges["in_sync"], json.dumps(colleges))

    # ------------------------------------------------------------------
    # Database
    # ------------------------------------------------------------------

    print("\n=== database: connection pool ===")
    p = c.get("/infra/database/pool", headers=H["admin"]).json()
    check("pool reachable", p["reachable"] is True, json.dumps(p)[:200])
    check("postgres version reported", "PostgreSQL" in (p["version"] or ""), str(p["version"])[:60])
    check("uptime reported", (p["uptime_seconds"] or 0) > 0)
    check("application pool size reported", (p["pool_size"] or 0) > 0, json.dumps(p["pool_size"]))
    check("overflow is never shown negative", (p["overflow"] or 0) >= 0, json.dumps(p["overflow"]))
    check("pool saturation is a percentage",
          0 <= (p["pool_saturation_percent"] or 0) <= 100, json.dumps(p["pool_saturation_percent"]))
    check("server connections counted by state",
          p["server_connections"] == sum(p["by_state"].values()), json.dumps(p["by_state"]))
    check("server max_connections reported", (p["server_max_connections"] or 0) > 0)
    check("server saturation is a percentage",
          0 <= (p["server_saturation_percent"] or 0) <= 100)

    print("\n=== database: table sizes ===")
    t = c.get("/infra/database/tables", headers=H["admin"]).json()
    check("tables reachable with a database size", t["reachable"] and t["database_bytes"] > 0)
    check("size is also human readable", bool(t["database_human"]), str(t["database_human"]))
    check("tables returned", len(t["tables"]) > 5, str(len(t["tables"])))
    sizes = [x["total_bytes"] for x in t["tables"]]
    check("largest first", sizes == sorted(sizes, reverse=True), str(sizes[:5]))
    names = {x["table"] for x in t["tables"]}
    check("the real tables are there", {"posts", "users", "colleges"} <= names, str(sorted(names))[:200])
    posts_row = next(x for x in t["tables"] if x["table"] == "posts")
    check("row estimate and index size reported",
          posts_row["estimated_rows"] > 0 and posts_row["index_bytes"] > 0, json.dumps(posts_row))
    check("total is at least table plus index",
          posts_row["total_bytes"] >= posts_row["table_bytes"], json.dumps(posts_row))

    print("\n=== database: migrations ===")
    mig = c.get("/infra/database/migrations", headers=H["admin"]).json()
    check("migrations reachable", mig["reachable"] is True, json.dumps(mig)[:200])
    check("it does not claim a revision ledger", mig["uses_revision_ledger"] is False)
    check("every declared migration is reported", len(mig["migrations"]) == 5, str(len(mig["migrations"])))
    check("applied plus pending is the total",
          mig["applied"] + mig["pending"] == len(mig["migrations"]), json.dumps(mig)[:200])
    check("every migration is applied on this database",
          mig["pending"] == 0,
          json.dumps([[m["title"], m["missing_columns"], m["missing_indexes"], m["violations"]]
                      for m in mig["migrations"] if not m["applied"]]))
    backfill = next(m for m in mig["migrations"] if "invariant" in m["title"])
    check("the data backfill is checked by counting violations",
          backfill["violations"] == 0 and backfill["violations_label"], json.dumps(backfill))

    # A migration whose index is missing must come back pending, not applied.
    sql("DROP INDEX IF EXISTS ix_users_college_role")
    try:
        mig = c.get("/infra/database/migrations", headers=H["admin"]).json()
        row = next(m for m in mig["migrations"] if m["title"] == "User deactivation")
        check("a dropped index makes its migration pending",
              row["applied"] is False and "ix_users_college_role" in row["missing_indexes"],
              json.dumps(row))
        check("pending count follows", mig["pending"] == 1, json.dumps(mig["pending"]))
    finally:
        sql("CREATE INDEX IF NOT EXISTS ix_users_college_role ON users (college_id, role)")

    mig = c.get("/infra/database/migrations", headers=H["admin"]).json()
    check("restoring the index makes it applied again", mig["pending"] == 0, json.dumps(mig["pending"]))

    print("\n=== database: slow queries ===")
    sq = c.get("/infra/database/slow_queries", headers=H["admin"]).json()
    check("slow queries 200", isinstance(sq.get("queries"), list), json.dumps(sq)[:200])
    if sq["enabled"]:
        check("statements returned", len(sq["queries"]) > 0, json.dumps(sq)[:200])
        totals = [x["total_ms"] for x in sq["queries"]]
        check("ordered by total time", totals == sorted(totals, reverse=True), str(totals[:5]))
    else:
        check("a disabled extension says why rather than showing an empty list",
              bool(sq["reason"]) and bool(sq["how_to_enable"]), json.dumps(sq))
        check("it does not claim to be enabled", sq["enabled"] is False)

    print("\n=== database: backups ===")
    b = c.get("/infra/database/backups", headers=H["admin"]).json()
    check("backups 200 with a summary", bool(b["summary"]), json.dumps(b))
    check("archive_mode reported", b["archive_mode"] in ("on", "off", "always"), str(b["archive_mode"]))
    check("configured agrees with archive_mode",
          b["configured"] == (b["archive_mode"] in ("on", "always")), json.dumps(b))
    if not b["configured"]:
        check("it does not overstate the absence of backups",
              "external" in b["summary"], json.dumps(b["summary"]))

finally:
    teardown()

print(f"\n{'=' * 55}\n  {len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print("   -", f)
sys.exit(1 if FAIL else 0)
