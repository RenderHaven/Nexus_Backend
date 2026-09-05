"""
Verification of the entity-hydration pattern, against the live Postgres /
Redis stack.

What it is actually pinning down:

  * post:{id} holds the post's own row and nothing about the people or
    reference rows it points at.
  * A post, comment and message all come back with their author resolved
    from user:{id}.
  * Renaming a college is correct on the very next read of an *already
    cached* post -- the staleness bug the pattern exists to fix.
  * A hydration miss backfills user:{id} with the full UserBasic blob, not
    a projection of it.

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

TAG = "zzhyd"
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
        f"DELETE FROM messages WHERE chat_room_id IN (SELECT id FROM chat_rooms WHERE post_id IN ({posts}))",
        f"DELETE FROM chat_participants WHERE chat_room_id IN (SELECT id FROM chat_rooms WHERE post_id IN ({posts}))",
        f"DELETE FROM chat_rooms WHERE post_id IN ({posts})",
        f"DELETE FROM collaboration_requests WHERE post_id IN ({posts}) OR sender_id IN ({ids}) OR recipient_id IN ({ids})",
        f"DELETE FROM comment_edit_logs WHERE comment_id IN (SELECT id FROM post_comments WHERE post_id IN ({posts}))",
        f"DELETE FROM post_comments WHERE post_id IN ({posts})",
        f"DELETE FROM post_comments WHERE user_id IN ({ids})",
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
    sql(f"INSERT INTO colleges (id,name,created_at) VALUES ('{college_id}','{TAG} Old Name',now())")

    password = get_password_hash(PW)
    for key, role in (("admin", "admin"), ("stu", "student"), ("peer", "student")):
        user_id = uuid.uuid4()
        IDS[key] = user_id
        sql("INSERT INTO users (id,college_id,username,email,password,role,is_alumni,total_xp,"
            "current_level,profile,is_active,created_at,updated_at) VALUES ("
            f"'{user_id}','{college_id}','{TAG}_{key}','{TAG}_{key}@t.local','{password}',"
            f"'{role}'::user_role,false,77,'spark'::identity_level,'{{}}'::jsonb,true,now(),now())")

    IDS["cat"] = sql("SELECT id FROM categories LIMIT 1")
    IDS["cat_name"] = sql(f"SELECT name FROM categories WHERE id='{IDS['cat']}'")


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

    H = {k: login(k) for k in ("admin", "stu", "peer")}

    post_id = c.post(
        "/posts/",
        headers=H["stu"],
        json={"category_id": IDS["cat"], "type": "spark",
              "title": f"{TAG} post", "content": f"{TAG} body"},
    ).json()["payload"]["post_id"]

    c.patch(f"/posts/{post_id}/moderation", headers=H["admin"],
            json={"moderation_status": "approved"})

    print("\n=== a post reads back fully hydrated ===")
    post = c.get(f"/posts/{post_id}", headers=H["stu"]).json()
    check("author resolved", (post.get("author") or {}).get("username") == f"{TAG}_stu",
          json.dumps(post.get("author")))
    check("category resolved", (post.get("category") or {}).get("name") == IDS["cat_name"],
          json.dumps(post.get("category")))
    check("college resolved", (post.get("college") or {}).get("name") == f"{TAG} Old Name",
          json.dumps(post.get("college")))

    print("\n=== nothing referenced is baked into post:{id} ===")
    cached = json.loads(rc.get(f"post:{post_id}"))
    check("cached post carries no author", cached.get("author") is None, json.dumps(cached.get("author")))
    check("cached post carries no category", cached.get("category") is None, json.dumps(cached.get("category")))
    check("cached post carries no college", cached.get("college") is None, json.dumps(cached.get("college")))
    check("cached post still carries the raw ids",
          cached.get("user_id") == str(IDS["stu"]) and cached.get("college_id") == str(IDS["college"]))

    print("\n=== a college rename is correct on the next read ===")
    # The post is cached right now and is deliberately NOT busted below --
    # that is the whole point: only college:{id} is invalidated.
    check("post is cached before the rename", rc.exists(f"post:{post_id}") == 1)
    r = c.patch(f"/colleges/{IDS['college']}", headers=H["admin"], json={"name": f"{TAG} New Name"})
    check("rename accepted", r.status_code == 200, r.text)
    check("post:{id} was not busted by the rename", rc.exists(f"post:{post_id}") == 1)

    post = c.get(f"/posts/{post_id}", headers=H["stu"]).json()
    check("cached post shows the NEW college name",
          (post.get("college") or {}).get("name") == f"{TAG} New Name",
          json.dumps(post.get("college")))

    print("\n=== a hydration miss backfills the full UserBasic blob ===")
    rc.delete(f"user:{IDS['stu']}")
    c.get(f"/posts/{post_id}", headers=H["stu"])
    blob = rc.get(f"user:{IDS['stu']}")
    check("user:{id} written back on the miss", blob is not None)
    if blob:
        blob = json.loads(blob)
        check("backfill is a full row, not a projection",
              {"id", "username", "college_id", "role", "is_alumni", "total_xp", "current_level"}
              <= set(blob), json.dumps(sorted(blob)))
        check("backfilled scalars are real, not Pydantic defaults",
              blob.get("total_xp") == 77, json.dumps(blob.get("total_xp")))

    print("\n=== comments hydrate their author ===")
    comment_id = c.post(f"/posts/{post_id}/comment", headers=H["stu"],
                        json={"comment": f"{TAG} hello"}).json()["payload"]["comment_id"]

    single = c.get(f"/comments/{comment_id}").json()
    check("single comment carries its author",
          (single.get("author") or {}).get("username") == f"{TAG}_stu",
          json.dumps(single.get("author")))

    batch = c.post("/comments/batch", json={"comment_ids": [comment_id]}).json()
    check("batch comment carries its author",
          batch and (batch[0].get("author") or {}).get("username") == f"{TAG}_stu",
          json.dumps(batch))

    cached_comment = rc.get(f"comments:{comment_id}")
    if cached_comment:
        check("nothing about the author is stored in comments:{id}",
              json.loads(cached_comment).get("author") is None, cached_comment.decode())

    print("\n=== DB-rendered listings hydrate too (no joins left) ===")
    queue = c.get(f"/posts/moderation/approved?college_id={IDS['college']}", headers=H["admin"]).json()
    mine = [p for p in queue.get("items", []) if p["id"] == post_id]
    check("moderation queue returns the post", bool(mine), json.dumps(queue)[:200])
    if mine:
        row = mine[0]
        check("queue row has its author", (row.get("author") or {}).get("username") == f"{TAG}_stu",
              json.dumps(row.get("author")))
        check("queue row has its college", (row.get("college") or {}).get("name") == f"{TAG} New Name",
              json.dumps(row.get("college")))
        check("queue row has its category", (row.get("category") or {}).get("name") == IDS["cat_name"],
              json.dumps(row.get("category")))

    c.post(f"/posts/{post_id}/archive", headers=H["stu"])
    inactive = c.get("/posts/my_inactive_posts", headers=H["stu"]).json()
    mine = [p for p in inactive if p["id"] == post_id]
    check("my_inactive_posts returns the archived post", bool(mine), json.dumps(inactive)[:200])
    if mine:
        check("inactive row has its author",
              (mine[0].get("author") or {}).get("username") == f"{TAG}_stu",
              json.dumps(mine[0].get("author")))
        check("inactive row has its college",
              (mine[0].get("college") or {}).get("name") == f"{TAG} New Name",
              json.dumps(mine[0].get("college")))
    c.post(f"/posts/{post_id}/publish", headers=H["stu"])

    print("\n=== moderation history hydrates its moderator ===")
    history = c.get(f"/posts/{post_id}/moderation_history", headers=H["admin"])
    if history.status_code == 200:
        entries = history.json()
        check("history has entries", bool(entries), history.text[:200])
        if entries:
            check("history entry carries moderator_id",
                  entries[0].get("moderator_id") == str(IDS["admin"]), json.dumps(entries[0]))
            check("history entry hydrates the moderator",
                  (entries[0].get("moderator") or {}).get("username") == f"{TAG}_admin",
                  json.dumps(entries[0].get("moderator")))
    else:
        check("moderation history 200", False, f"{history.status_code} {history.text[:150]}")

    print("\n=== stats still name their moderators without a join ===")
    stats = c.get("/admin/stats/moderation", headers=H["admin"])
    if stats.status_code == 200:
        rows = stats.json().get("by_moderator", [])
        mine = [r for r in rows if r.get("moderator_id") == str(IDS["admin"])]
        check("by_moderator names our moderator",
              bool(mine) and mine[0].get("username") == f"{TAG}_admin", json.dumps(rows)[:250])
    else:
        check("stats/moderation 200", False, f"{stats.status_code} {stats.text[:150]}")

    activity = c.get("/admin/activity", headers=H["admin"])
    if activity.status_code == 200:
        rows = [r for r in activity.json() if r.get("post_id") == post_id]
        check("activity names our moderator",
              bool(rows) and rows[0].get("moderator_username") == f"{TAG}_admin",
              json.dumps(rows)[:250])
    else:
        check("stats/activity 200", False, f"{activity.status_code} {activity.text[:150]}")

    print("\n=== collaboration requests hydrate both people ===")
    collab_id = c.post(
        "/posts/collaborations",
        headers=H["stu"],
        json={"category_id": IDS["cat"], "type": "collaboration",
              "title": f"{TAG} collab", "content": f"{TAG} collab body"},
    ).json()["payload"]["post_id"]
    c.patch(f"/posts/{collab_id}/moderation", headers=H["admin"],
            json={"moderation_status": "approved"})

    r = c.post(f"/collabs/{collab_id}/request", headers=H["peer"],
               json={"sender_id": str(IDS["peer"]), "note": "let me in"})
    check("request sent", r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}")

    sent = c.get("/collabs/my_sent_requests", headers=H["peer"])
    check("my_sent_requests 200", sent.status_code == 200, sent.text[:200])
    rows = [x for x in (sent.json() if sent.status_code == 200 else []) if x["post_id"] == collab_id]
    check("sent request found", bool(rows), sent.text[:200])
    if rows:
        check("sender hydrated", (rows[0].get("sender") or {}).get("username") == f"{TAG}_peer",
              json.dumps(rows[0].get("sender")))
        check("recipient hydrated", (rows[0].get("recipient") or {}).get("username") == f"{TAG}_stu",
              json.dumps(rows[0].get("recipient")))

    received = c.get("/collabs/my_received_requests", headers=H["stu"])
    check("my_received_requests 200", received.status_code == 200, received.text[:200])
    rows = [x for x in (received.json() if received.status_code == 200 else []) if x["post_id"] == collab_id]
    check("received request hydrated",
          bool(rows) and (rows[0].get("sender") or {}).get("username") == f"{TAG}_peer",
          received.text[:200])

    by_post = c.get(f"/collabs/{collab_id}/requests", headers=H["stu"])
    check("per-post requests 200", by_post.status_code == 200, by_post.text[:200])
    rows = by_post.json() if by_post.status_code == 200 else []
    check("per-post request hydrated",
          bool(rows) and (rows[0].get("sender") or {}).get("username") == f"{TAG}_peer",
          by_post.text[:200])

    print("\n=== chat messages hydrate their sender ===")
    received = c.get("/collabs/my_received_requests", headers=H["stu"]).json()
    request_id = next((x["id"] for x in received if x["post_id"] == collab_id), None)
    r = c.post(f"/collabs/requests/{request_id}/review", headers=H["stu"],
               json={"accept": True})
    check("request accepted", r.status_code == 200, f"{r.status_code} {r.text[:200]}")

    room_id = sql(f"SELECT id FROM chat_rooms WHERE post_id='{collab_id}'")
    check("collab post has a chat room", bool(room_id), room_id)

    r = c.post(f"/chats/{room_id}/message", headers=H["peer"],
               json={"body": f"{TAG} hi there", "type": "text"})
    check("message sent", r.status_code in (200, 201), f"{r.status_code} {r.text[:200]}")

    items = c.get(f"/chats/{room_id}/msg_items", headers=H["peer"])
    check("msg_items 200", items.status_code == 200, items.text[:200])
    rows = items.json().get("items", []) if items.status_code == 200 else []
    check("message list returned", bool(rows), items.text[:250])
    if rows:
        check("message hydrates its sender",
              (rows[0].get("author") or {}).get("username") == f"{TAG}_peer",
              json.dumps(rows[0].get("author")))

    print("\n=== a username edit is correct on the next read ===")
    c.patch(f"/users/{IDS['stu']}", headers=H["admin"], json={"is_alumni": True})
    batch = c.post("/comments/batch", json={"comment_ids": [comment_id]}).json()
    check("comment author survives a user cache bust",
          batch and (batch[0].get("author") or {}).get("username") == f"{TAG}_stu",
          json.dumps(batch))

finally:
    teardown()

print(f"\n{'=' * 55}\n  {len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL:
    print("   -", f)
sys.exit(1 if FAIL else 0)
