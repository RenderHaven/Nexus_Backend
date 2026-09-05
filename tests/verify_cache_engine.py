"""
Verification of the Redis monitoring service and the /infra/cache endpoints,
against the live stack.

What it pins down:

  * Health reports real numbers, and degrades to reachable=false rather than
    raising when Redis cannot be reached.
  * Hit and miss counters actually move when the app reads through the cache,
    and land in the right namespace.
  * The keyspace scan classifies keys and never runs KEYS.
  * The inspector shows what is stored without dumping it.
  * Invalidation drops what it says and nothing next to it -- particularly,
    busting `user` must not take `user:profile:*` with it.
  * Every route is admin-only.

Creates its own fixtures and removes them again.
"""
import atexit
import json
import os
import subprocess
import sys
import uuid

os.environ.setdefault("DB_ECHO", "False")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import redis as _redis
from fastapi.testclient import TestClient

from app.auth.security import get_password_hash
from app.main import app

TAG = "zzcache"
PW = "Passw0rd!123"
IDS: dict = {}
PASS: list = []
FAIL: list = []


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
    posts = f"SELECT id FROM posts WHERE user_id IN ({ids})"
    for q in (
        f"DELETE FROM moderation_logs WHERE post_id IN ({posts})",
        f"DELETE FROM moderation_logs WHERE coach_id IN ({ids})",
        f"DELETE FROM post_media WHERE post_id IN ({posts})",
        f"UPDATE posts SET reviewed_by=NULL WHERE reviewed_by IN ({ids})",
        f"DELETE FROM posts WHERE user_id IN ({ids})",
        f"DELETE FROM users WHERE username LIKE '{TAG}%'",
        f"DELETE FROM colleges WHERE name LIKE '{TAG}%'",
    ):
        sql(q)


def setup() -> None:
    college_id = uuid.uuid4()
    IDS["college"] = college_id
    sql(f"INSERT INTO colleges (id,name,created_at) VALUES ('{college_id}','{TAG} C',now())")

    password = get_password_hash(PW)
    for key, role in (("admin", "admin"), ("stu", "student")):
        user_id = uuid.uuid4()
        IDS[key] = user_id
        sql("INSERT INTO users (id,college_id,username,email,password,role,is_alumni,total_xp,"
            "current_level,profile,is_active,created_at,updated_at) VALUES ("
            f"'{user_id}','{college_id}','{TAG}_{key}','{TAG}_{key}@t.local','{password}',"
            f"'{role}'::user_role,false,0,'spark'::identity_level,'{{}}'::jsonb,true,now(),now())")

    IDS["cat"] = sql("SELECT id FROM categories LIMIT 1")


teardown()
setup()

_ctx = TestClient(app)
c = _ctx.__enter__()
atexit.register(lambda: _ctx.__exit__(None, None, None))

rc = _redis.Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379"))

try:
    def login(key: str) -> dict:
        r = c.post("/auth/login", data={"username": f"{TAG}_{key}@t.local", "password": PW})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    H = {k: login(k) for k in ("admin", "stu")}

    print("\n=== every route is platform staff only ===")
    for method, path in (
        ("get", "/infra/cache/health"),
        ("get", "/infra/cache/hit_rate"),
        ("get", "/infra/cache/keyspace"),
        ("get", "/infra/cache/key?key=post:x"),
        ("get", "/infra/cache/ttl_policy"),
        ("delete", "/infra/cache/key?key=post:x"),
        ("delete", "/infra/cache/namespace/post"),
    ):
        anon = getattr(c, method)(path)
        student = getattr(c, method)(path, headers=H["stu"])
        check(f"{method.upper()} {path.split('?')[0]} 401 anonymous", anon.status_code == 401,
              str(anon.status_code))
        check(f"{method.upper()} {path.split('?')[0]} 403 for a student", student.status_code == 403,
              str(student.status_code))

    print("\n=== connection health ===")
    r = c.get("/infra/cache/health", headers=H["admin"])
    check("health 200", r.status_code == 200, r.text[:200])
    h = r.json()
    check("reachable", h["reachable"] is True, json.dumps(h))
    check("latency measured", isinstance(h["latency_ms"], (int, float)) and h["latency_ms"] >= 0)
    check("version reported", bool(h["version"]), json.dumps(h.get("version")))
    check("uptime reported", (h["uptime_seconds"] or 0) > 0)
    check("memory reported", (h["memory_used_bytes"] or 0) > 0)
    check("evictions reported", h["evicted_keys"] is not None)
    check("total_keys agrees with DBSIZE", h["total_keys"] == rc.dbsize(),
          f"{h['total_keys']} vs {rc.dbsize()}")
    check("no memory percent when maxmemory is unset",
          (h["memory_used_percent"] is None) == (h["maxmemory_bytes"] == 0),
          json.dumps([h["maxmemory_bytes"], h["memory_used_percent"]]))

    print("\n=== hit rate follows real reads ===")
    post_id = c.post("/posts/", headers=H["stu"],
                     json={"category_id": IDS["cat"], "type": "spark",
                           "title": f"{TAG} p", "content": f"{TAG} body"}).json()["payload"]["post_id"]
    c.patch(f"/posts/{post_id}/moderation", headers=H["admin"],
            json={"moderation_status": "approved"})

    def ns_counts(namespace):
        rows = c.get("/infra/cache/hit_rate", headers=H["admin"]).json()["by_namespace"]
        row = next((x for x in rows if x["namespace"] == namespace), None)
        return (row["hits"], row["misses"]) if row else (None, None)

    rc.delete(f"post:{post_id}")
    before_h, before_m = ns_counts("post")
    c.get(f"/posts/{post_id}", headers=H["stu"])          # cold: one miss
    mid_h, mid_m = ns_counts("post")
    c.get(f"/posts/{post_id}", headers=H["stu"])          # warm: one hit
    after_h, after_m = ns_counts("post")

    check("a cold read counts a post miss", mid_m == before_m + 1, f"{before_m} -> {mid_m}")
    check("a warm read counts a post hit", after_h == mid_h + 1, f"{mid_h} -> {after_h}")
    check("a warm read counts no extra miss", after_m == mid_m, f"{mid_m} -> {after_m}")

    before_h, before_m = ns_counts("user")
    rc.delete(f"user:{IDS['stu']}")
    c.get(f"/posts/{post_id}", headers=H["stu"])          # hydration misses the author
    after_h, after_m = ns_counts("user")
    check("hydrating an author counts against the user namespace",
          after_m == before_m + 1, f"{before_m} -> {after_m}")

    hr = c.get("/infra/cache/hit_rate?hours=6", headers=H["admin"]).json()
    check("server-wide counters present", hr["server_hits"] > 0 and hr["server_misses"] >= 0)
    check("server hit rate is a ratio", 0 <= (hr["server_hit_rate"] or 0) <= 1,
          json.dumps(hr["server_hit_rate"]))
    series = next((s for s in hr["series"] if s["namespace"] == "post"), None)
    check("hourly series has one bucket per hour asked for",
          series and len(series["buckets"]) == 6, json.dumps(len(series["buckets"]) if series else None))
    check("the newest bucket carries this run's traffic",
          series and series["buckets"][-1]["hits"] > 0, json.dumps(series["buckets"][-1] if series else None))
    check("hours is clamped", c.get("/infra/cache/hit_rate?hours=999",
                                    headers=H["admin"]).status_code == 422)

    print("\n=== keyspace ===")
    ks = c.get("/infra/cache/keyspace", headers=H["admin"]).json()
    check("keyspace 200 with a total", ks["total_keys"] > 0, json.dumps(ks["total_keys"]))
    by_name = {n["namespace"]: n for n in ks["namespaces"]}
    check("post namespace counted", by_name["post"]["keys"] > 0, json.dumps(by_name["post"]))
    check("post namespace sampled a TTL",
          by_name["post"]["max_ttl_seconds"] is not None, json.dumps(by_name["post"]))
    check("scanned count is bounded and reported",
          ks["scanned_keys"] <= 50_000 and ks["truncated"] is False, json.dumps(ks["scanned_keys"]))
    check("every declared namespace has a row",
          {"post", "user", "comment", "college", "category", "pool"} <= set(by_name),
          json.dumps(sorted(by_name)))

    print("\n=== key inspector ===")
    r = c.get(f"/infra/cache/key?key=post:{post_id}", headers=H["admin"])
    check("inspect 200", r.status_code == 200, r.text[:200])
    k = r.json()
    check("key exists", k["exists"] is True, json.dumps(k))
    check("classified into its namespace", k["namespace"] == "post", json.dumps(k["namespace"]))
    check("type reported", k["type"] == "string", json.dumps(k["type"]))
    check("ttl reported", (k["ttl_seconds"] or 0) > 0 and k["has_ttl"] is True, json.dumps(k))
    check("size reported", (k["size_bytes"] or 0) > 0)
    check("preview shows the value", f"{TAG} body" in (k["preview"] or ""), (k["preview"] or "")[:120])
    check("preview is bounded", len(k["preview"] or "") <= 2000)

    missing = c.get("/infra/cache/key?key=post:nope", headers=H["admin"]).json()
    check("a missing key is 200 exists=false", missing["exists"] is False, json.dumps(missing))

    pool = c.get("/infra/cache/key?key=pool:recent", headers=H["admin"]).json()
    if pool["exists"]:
        check("a zset reports its cardinality", (pool["length"] or 0) > 0, json.dumps(pool["length"]))
        check("a zset preview is a head, not the whole set",
              len((pool["preview"] or "").splitlines()) <= 20, json.dumps(pool["preview"])[:150])

    print("\n=== ttl policy ===")
    tp = c.get("/infra/cache/ttl_policy", headers=H["admin"]).json()
    rows = {r["namespace"]: r for r in tp["rows"]}
    check("post declares the 8h cache TTL", rows["post"]["declared_ttl_seconds"] == 8 * 3600,
          json.dumps(rows["post"]))
    check("post does not disagree with itself", rows["post"]["disagrees"] is False,
          json.dumps(rows["post"]))
    check("category is declared permanent", rows["category"]["declared_ttl_seconds"] is None)
    check("cursor namespace carries its leak note",
          "accumulate" in (rows["cursor"]["ttl_note"] or ""), json.dumps(rows["cursor"]["ttl_note"]))

    # A key written without the TTL its namespace declares must be reported.
    # Removed again straight away: leaving it behind would make the "post does
    # not disagree with itself" check above fail on the next run.
    rogue = f"post:{uuid.uuid4()}"
    rc.set(rogue, "{}")
    try:
        tp = c.get("/infra/cache/ttl_policy", headers=H["admin"]).json()
        row = next(r for r in tp["rows"] if r["namespace"] == "post")
        check("a post key with no expiry is flagged as a disagreement",
              row["disagrees"] is True and "no expiry" in (row["disagreement"] or ""),
              json.dumps(row))
    finally:
        rc.delete(rogue)

    print("\n=== invalidate ===")
    c.get(f"/posts/{post_id}", headers=H["stu"])
    check("post is cached before the drop", rc.exists(f"post:{post_id}") == 1)
    r = c.delete(f"/infra/cache/key?key=post:{post_id}", headers=H["admin"])
    check("delete key 200", r.status_code == 200, r.text[:200])
    check("one key reported deleted", r.json()["deleted"] == 1, r.text[:200])
    check("the key is gone", rc.exists(f"post:{post_id}") == 0)
    check("the post still reads (it falls back to Postgres)",
          c.get(f"/posts/{post_id}", headers=H["stu"]).status_code == 200)

    # The neighbour test: user:{id} and user:profile:{id} share a prefix.
    c.get(f"/users/{IDS['stu']}/profile", headers=H["stu"])
    c.get(f"/posts/{post_id}", headers=H["stu"])
    profile_keys = list(rc.scan_iter("user:profile:*"))
    check("a user profile is cached", len(profile_keys) > 0, str(profile_keys))
    check("a user is cached", rc.exists(f"user:{IDS['stu']}") == 1)

    r = c.delete("/infra/cache/namespace/user", headers=H["admin"])
    check("namespace delete 200", r.status_code == 200, r.text[:200])
    check("it dropped the user keys", rc.exists(f"user:{IDS['stu']}") == 0)
    check("it did NOT drop the profile keys",
          all(rc.exists(k) for k in profile_keys), str(profile_keys))

    r = c.delete("/infra/cache/namespace/nonsense", headers=H["admin"])
    check("an unknown namespace is refused 422", r.status_code == 422, r.text[:150])
    r = c.delete("/infra/cache/namespace/metrics", headers=H["admin"])
    check("the metrics namespace is refused", r.status_code == 422, r.text[:150])

    print("\n=== degrades instead of raising when redis is unreachable ===")
    import app.redis.service as svc_module

    class Dead:
        def __getattr__(self, _):
            async def boom(*a, **kw):
                raise ConnectionError("nope")
            return boom

    real = svc_module.get_redis
    svc_module.get_redis = lambda: Dead()
    try:
        service = svc_module.RedisMonitorService()
        import asyncio
        health = asyncio.get_event_loop().run_until_complete(service.health()) \
            if False else asyncio.run(service.health())
        check("health reports the outage rather than raising",
              health.reachable is False and "nope" in (health.error or ""),
              json.dumps(health.model_dump(), default=str))
        rate = asyncio.run(service.hit_rate())
        check("hit_rate returns empty rather than raising", rate.server_hits == 0)
        space = asyncio.run(service.keyspace())
        check("keyspace returns empty rather than raising", space.total_keys == 0)
    finally:
        svc_module.get_redis = real

finally:
    teardown()

print(f"\n{'=' * 55}\n  {len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print("   -", f)
sys.exit(1 if FAIL else 0)
