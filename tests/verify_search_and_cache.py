"""Search-index and Redis-cache side effects of moderation + deactivation."""
import os, sys, uuid, time, json, subprocess, atexit
sys.path.insert(0, "/home/vikram/Desktop/Nexus/backend")
from fastapi.testclient import TestClient
from app.main import app
from app.auth.security import get_password_hash

PW, TAG = "TestPass123!", "zzidx"
PASS, FAIL = [], []
def check(n, c, d=""):
    (PASS if c else FAIL).append(n)
    print(f"  {'PASS' if c else 'FAIL'}  {n}" + (f"   [{d}]" if d and not c else ""))

def sql(q):
    r = subprocess.run(["docker","exec","-i","college-social-postgres","psql","-U","postgres",
                        "-d","college_social","-tAc",q], capture_output=True, text=True)
    if r.returncode: raise RuntimeError(r.stderr.strip())
    return r.stdout.strip()

def os_get(index, doc_id):
    r = subprocess.run(["curl","-s","-o","/dev/null","-w","%{http_code}",
                        f"http://localhost:9200/{index}/_doc/{doc_id}"], capture_output=True, text=True)
    return r.stdout.strip()

def os_refresh():
    subprocess.run(["curl","-s","-XPOST","http://localhost:9200/_refresh"], capture_output=True)

IDS={}
def teardown():
    ids=f"SELECT id FROM users WHERE username LIKE '{TAG}%'"
    posts=f"SELECT id FROM posts WHERE user_id IN ({ids})"
    for q in (f"DELETE FROM moderation_logs WHERE post_id IN ({posts})",
              f"DELETE FROM moderation_logs WHERE coach_id IN ({ids})",
              f"DELETE FROM post_media WHERE post_id IN ({posts})",
              f"UPDATE posts SET reviewed_by=NULL WHERE reviewed_by IN ({ids})",
              f"DELETE FROM posts WHERE user_id IN ({ids})",
              f"DELETE FROM users WHERE username LIKE '{TAG}%'",
              f"DELETE FROM colleges WHERE name LIKE '{TAG}%'"): sql(q)

def setup():
    cA=uuid.uuid4(); IDS["cA"]=cA
    sql(f"INSERT INTO colleges (id,name,created_at) VALUES ('{cA}','{TAG} C',now())")
    pw=get_password_hash(PW)
    for key,role in (("mod","moderator"),("stu","student")):
        uid=uuid.uuid4(); IDS[key]=uid
        sql("INSERT INTO users (id,college_id,username,email,password,role,is_alumni,total_xp,"
            "current_level,profile,is_active,created_at,updated_at) VALUES ("
            f"'{uid}','{cA}','{TAG}_{key}','{TAG}_{key}@t.local','{pw}','{role}'::user_role,"
            "false,0,'spark'::identity_level,'{}'::jsonb,true,now(),now())")
    IDS["cat"]=sql("SELECT id FROM categories LIMIT 1")

teardown(); setup()
_C=TestClient(app); c=_C.__enter__(); atexit.register(lambda: _C.__exit__(None,None,None))

try:
    def login(k):
        r=c.post("/auth/login", data={"username":f"{TAG}_{k}@t.local","password":PW})
        return {"Authorization": f"Bearer {r.json()['access_token']}"}
    H={k:login(k) for k in ("mod","stu")}

    prefix = os.environ.get("OPENSEARCH_INDEX_PREFIX","")
    POSTS, USERS = f"{prefix}posts", f"{prefix}users"

    r=c.post("/posts/", headers=H["stu"], json={"category_id":IDS["cat"],"type":"spark",
              "title":f"{TAG} indexed","content":f"{TAG} searchable body"})
    pid=r.json()["payload"]["post_id"]
    os_refresh(); time.sleep(0.4)

    print("\n=== search index follows moderation ===")
    check("pending post NOT in index", os_get(POSTS,pid)=="404", os_get(POSTS,pid))
    c.patch(f"/posts/{pid}/moderation", headers=H["mod"], json={"moderation_status":"approved"})
    os_refresh(); time.sleep(0.4)
    check("approved post IS in index", os_get(POSTS,pid)=="200", os_get(POSTS,pid))
    c.patch(f"/posts/{pid}/moderation", headers=H["mod"], json={"moderation_status":"hold"})
    os_refresh(); time.sleep(0.4)
    check("held post removed from index", os_get(POSTS,pid)=="404", os_get(POSTS,pid))
    c.patch(f"/posts/{pid}/moderation", headers=H["mod"], json={"moderation_status":"approved"})
    os_refresh(); time.sleep(0.4)
    check("reverted post back in index", os_get(POSTS,pid)=="200", os_get(POSTS,pid))

    print("\n=== search index follows deactivation ===")
    uid=str(IDS["stu"])
    # The fixture users were inserted with raw SQL, so nothing has indexed
    # them yet. One no-op write through the service puts them in.
    c.post(f"/users/{uid}/activate", headers=H["mod"])
    c.patch(f"/users/{uid}", headers=H["mod"], json={"is_alumni": False})
    os_refresh(); time.sleep(0.4)
    check("active user IS in index", os_get(USERS,uid)=="200", os_get(USERS,uid))
    c.post(f"/users/{uid}/deactivate", headers=H["mod"])
    os_refresh(); time.sleep(0.4)
    check("deactivated user removed from index", os_get(USERS,uid)=="404", os_get(USERS,uid))
    check("their post also removed from index", os_get(POSTS,pid)=="404", os_get(POSTS,pid))
    check("their post is_active=false in DB", sql(f"SELECT is_active FROM posts WHERE id='{pid}'")=="f")
    c.post(f"/users/{uid}/activate", headers=H["mod"])
    os_refresh(); time.sleep(0.4)
    check("reactivated user back in index", os_get(USERS,uid)=="200", os_get(USERS,uid))
    check("their post back in index", os_get(POSTS,pid)=="200", os_get(POSTS,pid))

    print("\n=== moderation_logs persisted ===")
    n=int(sql(f"SELECT count(*) FROM moderation_logs WHERE post_id='{pid}'"))
    check("rows written to moderation_logs (3 decisions so far)", n==3, f"got {n}")
    acts=sql(f"SELECT string_agg(action::text,',' ORDER BY created_at) FROM moderation_logs WHERE post_id='{pid}'")
    check("actions recorded in order", acts=="approve,hold,approve", acts)
    check("coach_id recorded", sql(f"SELECT count(DISTINCT coach_id) FROM moderation_logs WHERE post_id='{pid}'")=="1")

    print("\n=== redis cache invalidation ===")
    import redis as _r
    rc=_r.Redis.from_url(os.environ.get("REDIS_URL","redis://localhost:6379"))
    c.get(f"/posts/{pid}")                      # warm the cache
    keys=[k for k in rc.scan_iter(f"*{pid}*")]
    check("post cached after a read", len(keys)>=1, str(keys))
    c.patch(f"/posts/{pid}/moderation", headers=H["mod"], json={"moderation_status":"hold"})
    keys=[k for k in rc.scan_iter(f"*{pid}*")]
    check("cache dropped on moderation write", len(keys)==0, str(keys))
finally:
    teardown()

print(f"\n{'='*55}\n  {len(PASS)} passed, {len(FAIL)} failed")
for f in FAIL: print("   -", f)
sys.exit(1 if FAIL else 0)
