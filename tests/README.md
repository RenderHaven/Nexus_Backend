# Verification suites

End-to-end checks for the post and user domains, run against the live
Postgres / Redis / OpenSearch stack from docker-compose. Each script creates
its own fixtures (colleges, users, posts) under a `zz...` name prefix and
removes them again, including after a crash: teardown runs first as well as
last, and matches on the prefix rather than on ids held in memory.

    PYTHONPATH=. python tests/verify_post_user_domains.py   # 103 checks
    PYTHONPATH=. python tests/verify_search_and_cache.py    #  15 checks

Both exit non-zero on the first failure count, so they drop straight into CI.

Two things to know if you extend them:

* Fixtures go in through `psql`, not the app's async session. The app's Redis
  client binds to the first event loop that touches it, so any async setup
  before TestClient leaves later requests talking to a closed loop.
* One `TestClient` portal is opened for the whole process for the same
  reason -- a per-request portal creates a new loop each time.
