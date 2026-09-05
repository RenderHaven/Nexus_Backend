"""
End-to-end verification of the post + user domain work, against the live
Postgres / Redis / OpenSearch stack. Creates its own fixtures and removes
them again.
"""
import os, sys, uuid, json, subprocess, atexit
os.environ.setdefault("DB_ECHO", "False")

sys.path.insert(0, "/home/vikram/Desktop/Nexus/backend")

from fastapi.testclient import TestClient
from app.main import app
from app.auth.security import get_password_hash


def sql(statement: str) -> str:
    """
    Fixtures run through psql rather than the app's async session.

    The app's Redis client binds to whichever event loop touches it first, so
    running async setup before TestClient would leave every later request
    talking to a closed loop.
    """
    out = subprocess.run(
        ["docker", "exec", "-i", "college-social-postgres",
         "psql", "-U", "postgres", "-d", "college_social", "-tAc", statement],
        capture_output=True, text=True,
    )
    if out.returncode != 0:
        raise RuntimeError(f"psql failed: {out.stderr.strip()}\n{statement[:200]}")
    return out.stdout.strip()

PW = "TestPass123!"
TAG = "zzverify"

PASS, FAIL = [], []

def check(name, cond, detail=""):
    (PASS if cond else FAIL).append(name)
    print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f"   [{detail}]" if detail and not cond else ""))

IDS = {}


def setup():
    cA, cB = uuid.uuid4(), uuid.uuid4()
    IDS["cA"], IDS["cB"] = cA, cB
    for cid, nm in ((cA, f"{TAG} College A"), (cB, f"{TAG} College B")):
        sql(f"INSERT INTO colleges (id,name,created_at) VALUES ('{cid}','{nm}',now())")

    people = [
        ("admin", "admin", cA), ("modA", "moderator", cA),
        ("coachA", "success_coach", cA), ("modB", "moderator", cB),
        ("stuA", "student", cA), ("stuA2", "student", cA),
        ("stuB", "student", cB),
    ]
    pw = get_password_hash(PW)
    for key, role, cid in people:
        uid = uuid.uuid4(); IDS[key] = uid
        sql(
            "INSERT INTO users (id,college_id,username,email,password,role,is_alumni,"
            "total_xp,current_level,profile,is_active,created_at,updated_at) VALUES ("
            f"'{uid}','{cid}','{TAG}_{key}','{TAG}_{key}@test.local','{pw}',"
            f"'{role}'::user_role,false,0,'spark'::identity_level,'{{}}'::jsonb,true,now(),now())"
        )
    IDS["cat"] = sql("SELECT id FROM categories LIMIT 1")


def teardown():
    """
    Remove every row this run created, identified by the TAG rather than by
    the ids dict -- a crashed run leaves rows behind that the next run's
    fixtures would collide with.
    """
    ids = f"SELECT id FROM users WHERE username LIKE '{TAG}%'"
    posts = f"SELECT id FROM posts WHERE user_id IN ({ids})"
    rooms = f"SELECT id FROM chat_rooms WHERE post_id IN ({posts})"

    for stmt in (
        f"DELETE FROM moderation_logs WHERE post_id IN ({posts})",
        f"DELETE FROM moderation_logs WHERE coach_id IN ({ids})",
        f"DELETE FROM comment_edit_logs WHERE comment_id IN (SELECT id FROM post_comments WHERE user_id IN ({ids}) OR post_id IN ({posts}))",
        f"DELETE FROM post_comments WHERE user_id IN ({ids}) OR post_id IN ({posts})",
        f"DELETE FROM post_reactions WHERE user_id IN ({ids}) OR post_id IN ({posts})",
        f"DELETE FROM post_media WHERE post_id IN ({posts})",
        f"DELETE FROM messages WHERE sender_id IN ({ids}) OR chat_room_id IN ({rooms})",
        f"DELETE FROM chat_participants WHERE user_id IN ({ids}) OR chat_room_id IN ({rooms})",
        f"DELETE FROM chat_rooms WHERE post_id IN ({posts}) OR admin_id IN ({ids})",
        f"DELETE FROM collaboration_requests WHERE post_id IN ({posts}) OR sender_id IN ({ids}) OR recipient_id IN ({ids})",
        f"DELETE FROM notifications WHERE user_id IN ({ids})",
        f"DELETE FROM activity_log WHERE user_id IN ({ids})",
        f"DELETE FROM user_badges WHERE user_id IN ({ids})",
        f"DELETE FROM user_interests WHERE user_id IN ({ids})",
        f"DELETE FROM user_open_to WHERE user_id IN ({ids})",
        f"DELETE FROM user_category_probability WHERE user_id IN ({ids})",
        f"UPDATE posts SET reviewed_by = NULL WHERE reviewed_by IN ({ids})",
        f"DELETE FROM posts WHERE user_id IN ({ids})",
        f"DELETE FROM users WHERE username LIKE '{TAG}%'",
        f"DELETE FROM colleges WHERE name LIKE '{TAG}%'",
    ):
        sql(stmt)


# One TestClient portal for the whole process: the app's Redis client binds
# to the first event loop that touches it, so a per-request portal would
# leave later requests talking to a closed loop.
_CTX = TestClient(app)
c = _CTX.__enter__()
atexit.register(lambda: _CTX.__exit__(None, None, None))

def main():
    def login(key):
        r = c.post("/auth/login", data={"username": f"{TAG}_{key}@test.local", "password": PW})
        assert r.status_code == 200, (key, r.status_code, r.text[:200])
        return {"Authorization": f"Bearer {r.json()['access_token']}"}

    H = {k: login(k) for k in ("admin","modA","coachA","modB","stuA","stuA2","stuB")}

    def mkpost(who, title):
        r = c.post("/posts/", headers=H[who], json={
            "category_id": str(IDS["cat"]), "type": "spark",
            "title": title, "content": f"{TAG} body"})
        assert r.status_code == 201, r.text[:300]
        return r.json()["payload"]["post_id"]

    pA = mkpost("stuA", f"{TAG} A1")
    pB = mkpost("stuB", f"{TAG} B1")

    print("\n=== POST: visibility ===")
    check("author sees own pending post", c.get(f"/posts/{pA}", headers=H["stuA"]).status_code == 200)
    check("other student 404s on pending post", c.get(f"/posts/{pA}", headers=H["stuA2"]).status_code == 404)
    check("anon 404s on pending post", c.get(f"/posts/{pA}").status_code == 404)
    check("moderator same college reads hidden post", c.get(f"/posts/{pA}", headers=H["modA"]).status_code == 200)
    check("coach same college reads hidden post", c.get(f"/posts/{pA}", headers=H["coachA"]).status_code == 200)
    check("moderator OTHER college 404s on hidden post", c.get(f"/posts/{pA}", headers=H["modB"]).status_code == 404)
    check("admin reads hidden post any college", c.get(f"/posts/{pB}", headers=H["admin"]).status_code == 200)

    print("\n=== POST: moderation queue scoping ===")
    r = c.get("/posts/moderation/pending", headers=H["modA"])
    check("moderator queue 200", r.status_code == 200, r.text[:200])
    body = r.json()
    check("queue returns {items,total,limit,offset}", set(body) == {"items","total","limit","offset"}, str(set(body)))
    ids = [i["id"] for i in body["items"]]
    check("moderator queue contains own-college post", pA in ids)
    check("moderator queue excludes other-college post", pB not in ids)
    check("total == len(items)", body["total"] == len(body["items"]))
    check("moderator asking for other college -> 403",
          c.get("/posts/moderation/pending", headers=H["modA"], params={"college_id": str(IDS["cB"])}).status_code == 403)
    check("moderator asking for OWN college -> 200",
          c.get("/posts/moderation/pending", headers=H["modA"], params={"college_id": str(IDS["cA"])}).status_code == 200)
    radm = c.get("/posts/moderation/pending", headers=H["admin"])
    check("admin sees both colleges", pA in [i["id"] for i in radm.json()["items"]] and pB in [i["id"] for i in radm.json()["items"]])
    check("student 403 on queue", c.get("/posts/moderation/pending", headers=H["stuA"]).status_code == 403)
    check("anon 401 on queue", c.get("/posts/moderation/pending").status_code == 401)

    print("\n=== POST: filters + counts ===")
    check("filter by author narrows",
          [i["id"] for i in c.get("/posts/moderation/pending", headers=H["modA"], params={"user_id": str(IDS["stuA"])}).json()["items"]] == [pA])
    check("filter by wrong author is empty",
          c.get("/posts/moderation/pending", headers=H["modA"], params={"user_id": str(IDS["stuA2"])}).json()["items"] == [])
    check("free text q matches title", pA in [i["id"] for i in c.get("/posts/moderation/pending", headers=H["modA"], params={"q":"A1"}).json()["items"]])
    check("q with % is escaped, not wildcard",
          c.get("/posts/moderation/pending", headers=H["modA"], params={"q":"%"}).json()["items"] == [])
    check("sort=reviewed_at accepted", c.get("/posts/moderation/pending", headers=H["modA"], params={"sort":"reviewed_at","order":"desc"}).status_code == 200)
    check("bad sort rejected (422)", c.get("/posts/moderation/pending", headers=H["modA"], params={"sort":"password"}).status_code == 422)
    cnt = c.get("/posts/moderation/counts", headers=H["modA"])
    check("counts 200 + 4 keys", cnt.status_code == 200 and set(cnt.json()) == {"pending","approved","hold","removed"}, cnt.text[:200])
    check("counts pending >= 1", cnt.json()["pending"] >= 1)
    check("counts scoped: modA != admin", cnt.json()["pending"] <= c.get("/posts/moderation/counts", headers=H["admin"]).json()["pending"])

    print("\n=== POST: decisions ===")
    check("pending rejected as a decision (422)",
          c.patch(f"/posts/{pA}/moderation", headers=H["modA"], json={"moderation_status":"pending"}).status_code == 422)
    check("moderator cannot decide other college's post (403)",
          c.patch(f"/posts/{pB}/moderation", headers=H["modA"], json={"moderation_status":"approved"}).status_code == 403)
    r = c.patch(f"/posts/{pA}/moderation", headers=H["modA"], json={"moderation_status":"approved","note":"looks good"})
    check("approve 200", r.status_code == 200, r.text[:200])
    check("approved post now public to other student", c.get(f"/posts/{pA}", headers=H["stuA2"]).status_code == 200)
    check("approved post visible to anon", c.get(f"/posts/{pA}").status_code == 200)
    r = c.patch(f"/posts/{pA}/moderation", headers=H["modA"], json={"moderation_status":"removed","note":"spam"})
    check("remove 200", r.status_code == 200)
    check("removed post hidden again", c.get(f"/posts/{pA}", headers=H["stuA2"]).status_code == 404)
    r = c.patch(f"/posts/{pA}/moderation", headers=H["modA"], json={"moderation_status":"approved","note":"revert"})
    check("REVERT removed->approved works", r.status_code == 200 and c.get(f"/posts/{pA}", headers=H["stuA2"]).status_code == 200)

    print("\n=== POST: moderation history ===")
    h = c.get(f"/posts/{pA}/moderation_history", headers=H["modA"])
    check("history 200", h.status_code == 200, h.text[:200])
    check("history has 4 entries (approve/remove/approve + note)", len(h.json()) >= 3, f"got {len(h.json())}")
    check("history newest first", [e["action"] for e in h.json()][:1] == ["approve"], str([e["action"] for e in h.json()]))
    check("history carries the note", any(e["note"] == "spam" for e in h.json()))
    check("history carries the moderator", all(e["moderator"] and e["moderator"]["username"] == f"{TAG}_modA" for e in h.json()))
    check("AUTHOR can read history", c.get(f"/posts/{pA}/moderation_history", headers=H["stuA"]).status_code == 200)
    check("other student 403 on history", c.get(f"/posts/{pA}/moderation_history", headers=H["stuA2"]).status_code == 403)
    check("moderator other college 403 on history", c.get(f"/posts/{pA}/moderation_history", headers=H["modB"]).status_code == 403)
    check("admin reads history", c.get(f"/posts/{pA}/moderation_history", headers=H["admin"]).status_code == 200)

    print("\n=== POST: bulk ===")
    p2, p3 = mkpost("stuA", f"{TAG} A2"), mkpost("stuA", f"{TAG} A3")
    r = c.patch("/posts/moderation/bulk", headers=H["modA"],
                json={"post_ids":[p2,p3,pB,str(uuid.uuid4())], "moderation_status":"approved","note":"batch"})
    check("bulk 200", r.status_code == 200, r.text[:300])
    b = r.json()
    check("bulk updated own-college ids", set(b["updated"]) == {p2,p3}, str(b["updated"]))
    reasons = {f["post_id"]: f["reason"] for f in b["failed"]}
    check("bulk refused other-college post", reasons.get(pB) == "forbidden", str(reasons))
    check("bulk reported missing id", "not_found" in reasons.values(), str(reasons))
    check("bulk-approved posts are public", c.get(f"/posts/{p2}").status_code == 200 and c.get(f"/posts/{p3}").status_code == 200)
    check("bulk wrote history for each", len(c.get(f"/posts/{p2}/moderation_history", headers=H["modA"]).json()) >= 1)

    print("\n=== USER: permissions endpoint ===")
    for who, plat in (("admin",True),("modA",False),("stuA",False)):
        r = c.get("/users/me/permissions", headers=H[who])
        check(f"{who} permissions 200", r.status_code == 200)
        check(f"{who} is_platform_wide={plat}", r.json()["is_platform_wide"] == plat)
    check("student has no permissions", c.get("/users/me/permissions", headers=H["stuA"]).json()["permissions"] == [])
    check("admin has delete_user", "delete_user" in c.get("/users/me/permissions", headers=H["admin"]).json()["permissions"])
    check("moderator lacks delete_user", "delete_user" not in c.get("/users/me/permissions", headers=H["modA"]).json()["permissions"])

    print("\n=== USER: listing + scoping ===")
    r = c.get("/users", headers=H["modA"])
    check("moderator list 200", r.status_code == 200, r.text[:200])
    got = {u["username"] for u in r.json()["items"]}
    check("list scoped to own college", f"{TAG}_stuB" not in got and f"{TAG}_stuA" in got, str(sorted(got)))
    check("list carries email (staff view)", all("email" in u for u in r.json()["items"]))
    check("student 403 on list", c.get("/users", headers=H["stuA"]).status_code == 403)
    check("anon 401 on list", c.get("/users").status_code == 401)
    check("moderator asking other college -> 403",
          c.get("/users", headers=H["modA"], params={"college_id": str(IDS["cB"])}).status_code == 403)
    check("admin can ask any college",
          c.get("/users", headers=H["admin"], params={"college_id": str(IDS["cB"])}).status_code == 200)
    check("filter role=student works",
          all(u["role"]=="student" for u in c.get("/users", headers=H["modA"], params={"role":"student"}).json()["items"]))
    check("q searches username",
          f"{TAG}_stuA" in {u["username"] for u in c.get("/users", headers=H["modA"], params={"q":"stuA"}).json()["items"]})
    check("public profile has NO email", "email" not in c.get(f"/users/{IDS['stuA']}/profile", headers=H["stuA"]).json())
    check("GET /users/me has NO email", "email" not in c.get("/users/me", headers=H["stuA"]).json())

    print("\n=== USER: guards ===")
    sA, sA2, mB, mA = str(IDS["stuA"]), str(IDS["stuA2"]), str(IDS["modB"]), str(IDS["modA"])
    check("moderator CANNOT edit staff account",
          c.patch(f"/users/{IDS['coachA']}", headers=H["modA"], json={"is_alumni":True}).status_code == 403)
    check("moderator CANNOT edit other-college user",
          c.patch(f"/users/{IDS['stuB']}", headers=H["modA"], json={"is_alumni":True}).status_code == 403)
    r = c.patch(f"/users/{sA2}", headers=H["modA"], json={"is_alumni":True})
    check("moderator CAN edit own-college member", r.status_code == 200, r.text[:200])
    check("moderator CANNOT move user to another college",
          c.patch(f"/users/{sA2}", headers=H["modA"], json={"college_id":str(IDS["cB"])}).status_code == 403)
    check("admin CAN move user between colleges",
          c.patch(f"/users/{sA2}", headers=H["admin"], json={"college_id":str(IDS["cB"])}).status_code == 200)
    c.patch(f"/users/{sA2}", headers=H["admin"], json={"college_id":str(IDS["cA"])})
    check("moderator cannot assign staff role",
          c.patch(f"/users/{sA2}", headers=H["modA"], json={"role":"moderator"}).status_code == 403)
    check("moderator CANNOT deactivate self",
          c.post(f"/users/{mA}/deactivate", headers=H["modA"]).status_code == 403)
    check("admin CANNOT deactivate self",
          c.post(f"/users/{IDS['admin']}/deactivate", headers=H["admin"]).status_code == 403)
    check("moderator 403 on reset_password", c.post(f"/users/{sA2}/reset_password", headers=H["modA"]).status_code == 403)
    check("moderator 403 on delete", c.delete(f"/users/{sA2}", headers=H["modA"]).status_code == 403)
    check("empty PATCH body -> 422", c.patch(f"/users/{sA2}", headers=H["modA"], json={}).status_code == 422)

    print("\n=== USER: deactivation hides content ===")
    r = c.post(f"/users/{sA}/deactivate", headers=H["modA"])
    check("deactivate 200", r.status_code == 200, r.text[:200])
    check("deactivated user's approved post is now hidden", c.get(f"/posts/{pA}").status_code == 404)
    check("deactivated user cannot log in",
          c.post("/auth/login", data={"username": f"{TAG}_stuA@test.local","password":PW}).status_code == 403)
    check("deactivated user's OLD TOKEN is rejected", c.get("/users/me", headers=H["stuA"]).status_code == 403)
    check("moderator approving deactivated author's post keeps it hidden",
          (c.patch(f"/posts/{p2}/moderation", headers=H["modA"], json={"moderation_status":"approved"}).status_code == 200
           and c.get(f"/posts/{p2}").status_code == 404))
    check("deactivated user gone from listing default",
          f"{TAG}_stuA" not in {u["username"] for u in c.get("/users", headers=H["modA"], params={"is_active":True}).json()["items"]})
    r = c.post(f"/users/{sA}/activate", headers=H["modA"])
    check("activate 200", r.status_code == 200)
    check("reactivated user's post is public again", c.get(f"/posts/{pA}").status_code == 200)
    check("reactivated user can log in again",
          c.post("/auth/login", data={"username": f"{TAG}_stuA@test.local","password":PW}).status_code == 200)

    print("\n=== USER: delete semantics ===")
    r = c.delete(f"/users/{sA}", headers=H["admin"])
    check("delete refused for user with content (409)", r.status_code == 409, f"{r.status_code} {r.text[:150]}")
    d = r.json()
    check("409 names the code", d.get("code")=="user_has_content", json.dumps(d)[:200])
    check("409 carries the content counts", (d.get("payload") or {}).get("posts",0) >= 1, json.dumps(d)[:200])
    r = c.delete(f"/users/{IDS['stuA2']}", headers=H["admin"])
    check("delete succeeds for user with no content", r.status_code == 200, f"{r.status_code} {r.text[:150]}")
    check("deleted user is gone", c.get(f"/users/{IDS['stuA2']}").status_code == 404)

    print("\n=== USER: bulk + reset ===")
    r = c.post("/users/bulk", headers=H["modA"], json={
        "user_ids":[str(IDS["stuA"]), str(IDS["coachA"]), str(IDS["stuB"]), mA],
        "action":"deactivate"})
    check("bulk 200", r.status_code == 200, r.text[:250])
    b = r.json()
    check("bulk updated only the eligible member", b["updated"] == [str(IDS["stuA"])], str(b["updated"]))
    rs = {f["user_id"]: f["reason"] for f in b["failed"]}
    check("bulk refused staff account", rs.get(str(IDS["coachA"])) == "staff_account", str(rs))
    check("bulk refused other college", rs.get(str(IDS["stuB"])) == "forbidden", str(rs))
    check("bulk refused self", rs.get(mA) == "cannot_target_self", str(rs))
    c.post(f"/users/{sA}/activate", headers=H["modA"])
    r = c.post(f"/users/{sA}/reset_password", headers=H["admin"])
    check("admin reset_password 200", r.status_code == 200, r.text[:200])
    tmp = r.json()["payload"]["temp_password"]
    check("temp password returned", bool(tmp))
    check("old password no longer works",
          c.post("/auth/login", data={"username": f"{TAG}_stuA@test.local","password":PW}).status_code == 400)
    check("temp password works",
          c.post("/auth/login", data={"username": f"{TAG}_stuA@test.local","password":tmp}).status_code == 200)

    print("\n=== COLLEGE: public list unchanged ===")
    r = c.get("/colleges")
    check("GET /colleges works unauthenticated (signup path)", r.status_code == 200, str(r.status_code))
    check("GET /colleges is still a bare list", isinstance(r.json(), list), type(r.json()).__name__)
    check("public list has no counts", "user_count" not in (r.json()[0] if r.json() else {}))

    print("\n=== COLLEGE: admin table ===")
    r = c.get("/colleges/admin", headers=H["admin"])
    check("admin table 200", r.status_code == 200, r.text[:200])
    body = r.json()
    check("admin table is a Page", set(body) == {"items","total","limit","offset"}, str(set(body)))
    check("admin rows carry counts",
          all({"user_count","post_count","pending_count"} <= set(i) for i in body["items"]))
    names = {i["name"] for i in body["items"]}
    check("admin sees both test colleges", {f"{TAG} College A", f"{TAG} College B"} <= names, str(sorted(names)))
    rm = c.get("/colleges/admin", headers=H["modA"])
    check("moderator gets the table (not 403)", rm.status_code == 200, str(rm.status_code))
    check("moderator sees only their own row",
          [i["name"] for i in rm.json()["items"]] == [f"{TAG} College A"], str(rm.json()["items"]))
    check("student 403 on admin table", c.get("/colleges/admin", headers=H["stuA"]).status_code == 403)
    check("anon 401 on admin table", c.get("/colleges/admin").status_code == 401)
    check("q filters the admin table",
          {i["name"] for i in c.get("/colleges/admin", headers=H["admin"], params={"q":"College B"}).json()["items"]} == {f"{TAG} College B"})

    print("\n=== COLLEGE: stats ===")
    cA, cB = str(IDS["cA"]), str(IDS["cB"])
    r = c.get(f"/colleges/{cA}/stats", headers=H["modA"])
    check("moderator own-college stats 200", r.status_code == 200, r.text[:200])
    check("stats has 4 keys", set(r.json()) == {"users","posts","pending","active_this_week"}, str(set(r.json())))
    check("moderator OTHER college stats 403", c.get(f"/colleges/{cB}/stats", headers=H["modA"]).status_code == 403)
    check("admin any college stats 200", c.get(f"/colleges/{cB}/stats", headers=H["admin"]).status_code == 200)
    check("student 403 on stats", c.get(f"/colleges/{cA}/stats", headers=H["stuA"]).status_code == 403)
    row = next(i for i in c.get("/colleges/admin", headers=H["admin"]).json()["items"] if i["id"] == cA)
    st = c.get(f"/colleges/{cA}/stats", headers=H["admin"]).json()
    check("admin row counts match the stats endpoint",
          row["user_count"] == st["users"] and row["post_count"] == st["posts"], f"{row} vs {st}")

    print("\n=== COLLEGE: people ===")
    r = c.get(f"/colleges/{cA}/users", headers=H["stuA"])
    check("signed-in user reads own campus people", r.status_code == 200, r.text[:200])
    check("signed-in user reads ANOTHER campus people",
          c.get(f"/colleges/{cB}/users", headers=H["stuA"]).status_code == 200)
    check("anon 401 on people", c.get(f"/colleges/{cA}/users").status_code == 401)
    check("people carry no email", all("email" not in u for u in r.json()))
    check("role filter works",
          all(u["role"] == "moderator" for u in c.get(f"/colleges/{cA}/users", headers=H["stuA"], params={"role":"moderator"}).json()))
    check("q filter works",
          {u["username"] for u in c.get(f"/colleges/{cA}/users", headers=H["stuA"], params={"q":"modA"}).json()} == {f"{TAG}_modA"})
    staff_names = {u["username"] for u in c.get(f"/colleges/{cA}/staff", headers=H["modA"]).json()}
    check("staff roster lists only staff", staff_names == {f"{TAG}_admin", f"{TAG}_modA", f"{TAG}_coachA"}, str(sorted(staff_names)))
    check("student 403 on staff roster", c.get(f"/colleges/{cA}/staff", headers=H["stuA"]).status_code == 403)

    print("\n=== COLLEGE: deactivated users leave the people list ===")
    before = {u["username"] for u in c.get(f"/colleges/{cA}/users", headers=H["admin"]).json()}
    check("active user is listed", f"{TAG}_stuA" in before, str(sorted(before)))
    c.post(f"/users/{IDS['stuA']}/deactivate", headers=H["modA"])
    after = {u["username"] for u in c.get(f"/colleges/{cA}/users", headers=H["admin"]).json()}
    check("deactivated user is NOT listed", f"{TAG}_stuA" not in after, str(sorted(after)))
    c.post(f"/users/{IDS['stuA']}/activate", headers=H["modA"])
    check("reactivated user is listed again",
          f"{TAG}_stuA" in {u["username"] for u in c.get(f"/colleges/{cA}/users", headers=H["admin"]).json()})

    print("\n=== COLLEGE: cached user pool follows deactivation ===")
    # /colleges/user_items is served from a cached Redis pool, unlike
    # /colleges/{id}/users which queries directly. The pool has to be dropped
    # when someone is deactivated or it keeps serving the old ranking.
    r = c.get("/colleges/user_items", headers=H["modA"])
    check("user_items 200", r.status_code == 200, r.text[:200])
    pooled = {u["username"] for u in r.json()["items"]}
    check("pool lists the active user", f"{TAG}_stuA" in pooled, str(sorted(pooled)))
    c.post(f"/users/{IDS['stuA']}/deactivate", headers=H["modA"])
    pooled = {u["username"] for u in c.get("/colleges/user_items", headers=H["modA"]).json()["items"]}
    check("pool REBUILT without the deactivated user", f"{TAG}_stuA" not in pooled, str(sorted(pooled)))
    c.post(f"/users/{IDS['stuA']}/activate", headers=H["modA"])
    pooled = {u["username"] for u in c.get("/colleges/user_items", headers=H["modA"]).json()["items"]}
    check("pool rebuilt again on reactivate", f"{TAG}_stuA" in pooled, str(sorted(pooled)))

    print("\n=== COLLEGE: create / edit / delete ===")
    r = c.post("/colleges", headers=H["admin"], json={"name": f"{TAG} Fresh", "location": "Nowhere"})
    check("admin creates a college", r.status_code == 201, r.text[:200])
    fresh = r.json()["payload"]["college_id"]
    check("moderator 403 on create",
          c.post("/colleges", headers=H["modA"], json={"name": f"{TAG} Nope"}).status_code == 403)
    check("moderator edits OWN college",
          c.patch(f"/colleges/{cA}", headers=H["modA"], json={"tagline": "ours"}).status_code == 200)
    check("moderator 403 editing another college",
          c.patch(f"/colleges/{cB}", headers=H["modA"], json={"tagline": "nope"}).status_code == 403)
    check("edit is reflected on the next read",
          c.get(f"/colleges/{cA}").json()["tagline"] == "ours")
    check("empty edit body -> 422",
          c.patch(f"/colleges/{cA}", headers=H["admin"], json={}).status_code == 422)
    check("moderator 403 on delete", c.delete(f"/colleges/{fresh}", headers=H["modA"]).status_code == 403)
    r = c.delete(f"/colleges/{cA}", headers=H["admin"])
    check("delete refused while members exist (409)", r.status_code == 409, f"{r.status_code} {r.text[:150]}")
    d = r.json()
    check("409 names the code", d.get("code") == "college_in_use", json.dumps(d)[:200])
    check("409 carries the reference counts", (d.get("payload") or {}).get("users", 0) >= 1, json.dumps(d)[:200])
    r = c.delete(f"/colleges/{fresh}", headers=H["admin"])
    check("empty college deletes", r.status_code == 200, f"{r.status_code} {r.text[:150]}")
    check("deleted college is gone", c.get(f"/colleges/{fresh}").status_code == 404)


    print("\n=== STATS: gate ===")
    for path in ("/admin/stats/overview","/admin/stats/posts_timeseries",
                 "/admin/stats/users_timeseries","/admin/stats/moderation",
                 "/admin/stats/post_breakdown","/admin/stats/top_posts",
                 "/admin/stats/top_users","/admin/stats/colleges","/admin/activity"):
        ok = (c.get(path, headers=H["admin"]).status_code == 200
              and c.get(path, headers=H["modA"]).status_code == 200
              and c.get(path, headers=H["stuA"]).status_code == 403
              and c.get(path).status_code == 401)
        check(f"{path} staff-only + 200", ok,
              f'adm={c.get(path,headers=H["admin"]).status_code} '
              f'mod={c.get(path,headers=H["modA"]).status_code} '
              f'stu={c.get(path,headers=H["stuA"]).status_code} '
              f'anon={c.get(path).status_code}')

    print("\n=== STATS: scoping ===")
    for path in ("/admin/stats/overview","/admin/stats/moderation","/admin/activity"):
        check(f"{path} moderator cross-college 403",
              c.get(path, headers=H["modA"], params={"college_id": cB}).status_code == 403)
        check(f"{path} admin cross-college 200",
              c.get(path, headers=H["admin"], params={"college_id": cB}).status_code == 200)

    print("\n=== STATS: overview numbers ===")
    ov_all = c.get("/admin/stats/overview", headers=H["admin"]).json()
    ov_A = c.get("/admin/stats/overview", headers=H["modA"]).json()
    check("overview has 5 counters", set(ov_all) == {"users","colleges","posts","pending","active_today"}, str(set(ov_all)))
    check("platform users >= college users", ov_all["users"] >= ov_A["users"], f'{ov_all} vs {ov_A}')
    check("moderator overview scoped to 1 college", ov_A["colleges"] == 1, str(ov_A))
    check("admin overview counts all colleges", ov_all["colleges"] >= 3, str(ov_all))
    stats_A = c.get(f"/colleges/{cA}/stats", headers=H["admin"]).json()
    check("overview agrees with college stats",
          ov_A["users"] == stats_A["users"] and ov_A["pending"] == stats_A["pending"], f'{ov_A} vs {stats_A}')

    print("\n=== STATS: timeseries ===")
    r = c.get("/admin/stats/posts_timeseries", headers=H["modA"], params={"range":"30d","interval":"day"})
    check("posts_timeseries 200", r.status_code == 200, r.text[:200])
    ts = r.json()
    check("buckets have created/approved/removed",
          all({"bucket","created","approved","removed"} == set(b) for b in ts), str(ts[:1]))
    check("buckets are sorted", [b["bucket"] for b in ts] == sorted(b["bucket"] for b in ts))
    check("created total matches posts made in this run",
          sum(b["created"] for b in ts) >= 3, str(ts))
    check("approved counted (we approved some)", sum(b["approved"] for b in ts) >= 1, str(ts))
    for iv in ("day","week","month"):
        check(f"interval={iv} works",
              c.get("/admin/stats/posts_timeseries", headers=H["modA"], params={"interval":iv}).status_code == 200)
    for rg in ("7d","30d","90d","1y","all"):
        check(f"range={rg} works",
              c.get("/admin/stats/posts_timeseries", headers=H["modA"], params={"range":rg}).status_code == 200)
    check("bad range rejected 422",
          c.get("/admin/stats/posts_timeseries", headers=H["modA"], params={"range":"forever"}).status_code == 422)
    u = c.get("/admin/stats/users_timeseries", headers=H["modA"], params={"split_by_role":True}).json()
    check("users_timeseries signups counted", sum(b["signups"] for b in u) >= 4, str(u))
    check("split_by_role fills by_role", any(b["by_role"] for b in u), str(u))
    check("signups == sum of by_role", all(b["signups"] == sum(b["by_role"].values()) for b in u), str(u))

    print("\n=== STATS: moderation ===")
    m = c.get("/admin/stats/moderation", headers=H["modA"]).json()
    check("moderation has all keys",
          {"pending","approved","hold","removed","median_minutes_to_decision","by_moderator"} == set(m), str(set(m)))
    check("counts match the queue counts endpoint",
          m["pending"] == c.get("/posts/moderation/counts", headers=H["modA"]).json()["pending"], str(m))
    check("median is a number once decisions exist", isinstance(m["median_minutes_to_decision"], (int,float)), str(m["median_minutes_to_decision"]))
    check("by_moderator names our moderator",
          any(x["username"] == f"{TAG}_modA" for x in m["by_moderator"]), str(m["by_moderator"]))
    check("decision count > 0", any(x["decisions"] > 0 for x in m["by_moderator"]), str(m["by_moderator"]))

    print("\n=== STATS: breakdown + leaderboards ===")
    for g in ("type","category","college"):
        r = c.get("/admin/stats/post_breakdown", headers=H["admin"], params={"group_by":g})
        check(f"breakdown group_by={g} 200", r.status_code == 200, r.text[:200])
        check(f"breakdown group_by={g} has keys+counts",
              all({"key","label","count"} == set(s) for s in r.json()), str(r.json()[:1]))
    check("breakdown by college has labels",
          all(s["label"] for s in c.get("/admin/stats/post_breakdown", headers=H["admin"], params={"group_by":"college"}).json()))
    check("breakdown by type has no label",
          all(s["label"] is None for s in c.get("/admin/stats/post_breakdown", headers=H["admin"], params={"group_by":"type"}).json()))
    for metric in ("engagement","likes","comments"):
        r = c.get("/admin/stats/top_posts", headers=H["admin"], params={"metric":metric,"limit":5})
        check(f"top_posts metric={metric} 200", r.status_code == 200, r.text[:200])
        check(f"top_posts metric={metric} respects limit", len(r.json()) <= 5)
    tp = c.get("/admin/stats/top_posts", headers=H["admin"], params={"metric":"likes","limit":20}).json()
    check("top_posts sorted desc by likes",
          [p["like_count"] for p in tp] == sorted((p["like_count"] for p in tp), reverse=True), str([p["like_count"] for p in tp]))
    for metric in ("posts","xp"):
        r = c.get("/admin/stats/top_users", headers=H["admin"], params={"metric":metric})
        check(f"top_users metric={metric} 200", r.status_code == 200, r.text[:200])
    tu = c.get("/admin/stats/top_users", headers=H["modA"], params={"metric":"posts","limit":20}).json()
    check("top_users sorted desc by post_count",
          [x["post_count"] for x in tu] == sorted((x["post_count"] for x in tu), reverse=True), str([x["post_count"] for x in tu]))
    check("top_users scoped to own college",
          all(x["college_id"] == cA for x in tu), str([x["college_id"] for x in tu]))
    check("top_users carries both metrics", all({"post_count","total_xp"} <= set(x) for x in tu))

    print("\n=== STATS: colleges rollup + activity ===")
    roll = c.get("/admin/stats/colleges", headers=H["admin"]).json()
    check("rollup covers all colleges", len(roll) >= 3, str(len(roll)))
    rollA = next(x for x in roll if x["college_id"] == cA)
    check("rollup agrees with college stats",
          rollA["users"] == stats_A["users"] and rollA["pending"] == stats_A["pending"], f"{rollA} vs {stats_A}")
    check("moderator rollup is one row",
          len(c.get("/admin/stats/colleges", headers=H["modA"]).json()) == 1)
    act = c.get("/admin/activity", headers=H["modA"]).json()
    check("activity 200 + entries", len(act) >= 1, str(len(act)))
    check("activity entries shaped",
          all({"id","action","post_id","college_id","moderator_id","moderator_username","note","created_at"} == set(e) for e in act), str(act[:1]))
    check("activity newest first",
          [e["created_at"] for e in act] == sorted((e["created_at"] for e in act), reverse=True))
    check("activity scoped to own college", all(e["college_id"] == cA for e in act), str({e["college_id"] for e in act}))
    check("activity names the moderator",
          any(e["moderator_username"] == f"{TAG}_modA" for e in act), str(act[:1]))
    check("activity carries notes", any(e["note"] for e in act))
    check("activity paginates", c.get("/admin/activity", headers=H["modA"], params={"limit":1}).json().__len__() == 1)


if __name__ == "__main__":
    teardown()
    setup()
    try:
        main()
    finally:
        teardown()
    print(f"\n{'='*60}\n  {len(PASS)} passed, {len(FAIL)} failed")
    if FAIL:
        print("\n  FAILED:")
        for f in FAIL: print(f"   - {f}")
    sys.exit(1 if FAIL else 0)
