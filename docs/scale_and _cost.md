# Nexus — Scale & Cost Estimation

## 1. Purpose

This document estimates the expected scale, infrastructure requirements, and operating costs of the **Nexus** platform.

The initial deployment is planned across **30+ colleges**, with approximately **500 students per college**.

The estimates below are intended to help us choose an appropriate architecture without over-engineering the system for the initial stage.

---

# 2. Initial User Scale

### Per College

| User Type | Users / College |
| --- | --- |
| Students | 500 |
| Staff / Faculty | 20 |
| College Admin | 1 |
| **Total** | **521** |

### Across 30 Colleges

| User Type | Calculation | Total |
| --- | --- | --- |
| Students | 30 × 500 | **15,000** |
| Staff / Faculty | 30 × 20 | **600** |
| College Admins | 30 × 1 | **30** |
| **Total Users** | 30 × 521 | **15,630** |

> **Initial target: \~15.6K registered users**

---

# 3. Growth Assumptions

The initial calculation assumes:

- 30 colleges

- 500 students per college

- 20 staff/faculty per college

- 1 college administrator per college

However, the architecture should not be designed only for 15K users.

### Suggested capacity targets

| Stage | Colleges | Approx. Users |
| --- | --- | --- |
| MVP | 5 | \~2,605 |
| Initial Launch | 30 | \~15,630 |
| Growth | 100 | \~52,100 |
| Large | 250 | \~130,250 |
| Very Large | 500 | \~260,500 |

The system should ideally be able to scale from **15K → 100K+ users** without requiring a complete architectural rewrite.

---

# 4. Important Scale Metrics

Registered users are not the same as system load.

We need to estimate:

- Daily Active Users (DAU)

- Monthly Active Users (MAU)

- Requests per user

- Peak concurrent users

- Peak requests per second

- Database reads

- Database writes

- File uploads

- Notifications

- Feed interactions

- Likes

- Comments

- Follows

- Messages

- Search requests

---

# 5. Initial Traffic Assumptions

For an initial estimate, assume:

### User Activity

| Metric | Conservative | Medium | Heavy |
| --- | --- | --- | --- |
| Registered users | 15,630 | 15,630 | 15,630 |
| DAU % | 10% | 30% | 50% |
| DAU | \~1,563 | \~4,689 | \~7,815 |
| Requests / active user / day | 50 | 100 | 200 |
| Daily API requests | \~78K | \~469K | \~1.56M |

These numbers are assumptions and should be replaced with real production metrics after launch.

---

# 6. Peak Traffic

Average traffic is not enough for infrastructure planning.

For example, if we receive:

**500K requests/day**

Average:

```text
500,000 / 86,400
≈ 5.8 requests/sec
```

But traffic will not be evenly distributed.

If peak traffic is approximately **10× average**:

```text
≈ 58 requests/sec peak
```

Therefore, the initial architecture should comfortably handle approximately:

```text
50–100 RPS
```

without requiring major scaling work.

For future growth, we should target:

```text
500+ RPS
```

with horizontal scaling.

---

# 7. Database Scale

The database will contain significantly more records than users.

Potential entities include:

- Users

- Colleges

- Posts

- Comments

- Likes

- Follows

- Notifications

- Events

- Groups

- Messages

- Media metadata

- User interactions

- Activity logs

For example, with:

```text
15,630 users
```

and an average of:

```text
100 interactions/user
```

we could already have:

```text
15,630 × 100
≈ 1.56 million interaction records
```

At larger scale:

```text
100K users × 100 interactions
= 10 million interactions
```

Therefore, interaction-heavy tables should be designed with proper indexing and potentially separate storage strategies.

---

# 8. Interaction Storage

Nexus may have high-volume relationships such as:

```text
User → Like → Post
User → Follow → User
User → Comment → Post
User → View → Post
User → Save → Post
```

These should not be stored as large arrays inside user or post records.

Instead, use relationship/interaction records.

Example:

```text
likes
----------------
user_id
post_id
created_at
```

With appropriate indexes:

```text
INDEX(user_id)
INDEX(post_id)
UNIQUE(user_id, post_id)
```

This allows efficient queries in both directions:

```text
Get posts liked by user
Get users who liked post
Check whether user liked post
```

---

# 9. Storage Estimation

Storage requirements will depend heavily on media.

### Database

Initial database size is expected to be relatively small compared with media storage.

Potential starting range:

```text
5–20 GB
```

with significant room for growth.

### Media

Images and videos can become the largest storage component.

Example:

If:

```text
10,000 images/month
× 2 MB/image
```

Then:

```text
20 GB/month
≈ 240 GB/year
```

Video storage can increase this dramatically.

Therefore:

> Media should not be stored directly inside the primary database.

Use object storage for:

- Images

- Videos

- Documents

- Profile pictures

- Attachments

---

# 10. Caching

Redis or another cache can be used for frequently accessed data.

Potential cache use cases:

- Sessions

- Authentication data

- Rate limiting

- Frequently accessed feeds

- Trending posts

- Counters

- Temporary data

- API response caching

- Background job queues

However:

> Redis should not automatically become the primary storage for relationships such as all likes/follows.

Persistent interaction data should remain in the primary database or a dedicated scalable datastore.

---

# 11. Search / Graph Requirements

Some Nexus features may eventually require graph-like queries.

Examples:

```text
User → follows → User

User → likes → Post

User → belongs_to → College

User → member_of → Group

Post → belongs_to → College

User → interacted_with → Post
```

Initially, these relationships can likely be handled using a relational database with properly indexed junction tables.

A graph database such as Neo4j should only be introduced if we have actual workloads that benefit from graph traversal.

---

# 12. Initial Infrastructure

A reasonable MVP architecture could be:

```text
                    ┌───────────────┐
                    │    Clients    │
                    │ Web / Mobile  │
                    └───────┬───────┘
                            │
                            ▼
                    ┌───────────────┐
                    │ Load Balancer │
                    └───────┬───────┘
                            │
                 ┌──────────┴──────────┐
                 │                     │
                 ▼                     ▼
          ┌────────────┐        ┌────────────┐
          │ API Server │        │ API Server │
          └─────┬──────┘        └─────┬──────┘
                │                     │
                └──────────┬──────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
              ▼                         ▼
        ┌───────────┐              ┌─────────┐
        │ PostgreSQL│              │  Redis  │
        └───────────┘              └─────────┘
              │
              │
              ▼
        ┌──────────────┐
        │ Object Store │
        │ Images/Media │
        └──────────────┘
```

---

# 13. Recommended Initial Stack

| Component | Suggested Technology |
| --- | --- |
| API | FastAPI |
| Primary DB | PostgreSQL |
| Cache | Redis |
| Object Storage | S3-compatible storage |
| Reverse Proxy | Nginx / Cloud Load Balancer |
| Background Jobs | Celery / RQ / dedicated worker |
| Authentication | JWT / OAuth where required |
| Search | PostgreSQL initially |
| Monitoring | Prometheus + Grafana / managed monitoring |
| Logs | Centralized logging |
| CDN | CDN for media/static assets |

---

# 14. Estimated Initial Monthly Cost

These are **rough planning estimates**, not final vendor pricing.

## Small MVP

Designed for:

```text
~5 colleges
~2.6K users
```

Possible monthly infrastructure:

| Component | Estimated Cost |
| --- | --- |
| API server | ₹1,000–₹3,000 |
| PostgreSQL | ₹1,000–₹3,000 |
| Redis | ₹500–₹1,500 |
| Object storage | ₹200–₹1,000 |
| CDN / bandwidth | ₹500–₹2,000 |
| Monitoring / logs | ₹0–₹1,000 |
| Backups | ₹300–₹1,000 |
| **Estimated total** | **₹3,500–₹12,500/month** |

---

# 15. Initial 30-College Deployment

For approximately:

```text
15,630 users
```

A reasonable starting infrastructure budget could be:

| Component | Estimated Monthly Cost |
| --- | --- |
| API / Compute | ₹3,000–₹8,000 |
| PostgreSQL | ₹2,000–₹6,000 |
| Redis | ₹1,000–₹3,000 |
| Object Storage | ₹1,000–₹5,000 |
| CDN / Bandwidth | ₹1,000–₹5,000 |
| Backups | ₹500–₹2,000 |
| Monitoring / Logs | ₹500–₹3,000 |
| **Estimated Total** | **₹9,000–₹32,000/month** |

Actual cost will depend heavily on:

- Cloud provider

- Region

- Media volume

- Bandwidth

- Database size

- API traffic

- Number of background jobs

- Notification volume

---

# 16. Scaling Strategy

We should avoid starting with a highly distributed architecture.

### Phase 1 — 0–30K users

Use:

```text
1–2 API servers
1 PostgreSQL instance
1 Redis instance
Object storage
CDN
```

Focus on:

- Good database schema

- Proper indexes

- Caching

- Pagination

- Rate limiting

- Monitoring

- Backups

### Phase 2 — 30K–100K users

Introduce:

```text
Multiple API servers
Read replicas
Dedicated workers
Queue system
Improved caching
Dedicated search if required
```

### Phase 3 — 100K+ users

Potentially introduce:

```text
Database sharding
Dedicated services
Distributed queues
Dedicated search infrastructure
Graph database where justified
Advanced observability
Multiple Redis instances
Regional infrastructure
```

---

# 17. Cost Scaling Model

Infrastructure cost should be treated as a function of:

```text
Cost =
Compute
+ Database
+ Cache
+ Storage
+ Bandwidth
+ CDN
+ Backups
+ Monitoring
+ Third-party APIs
```

User count alone is not enough to predict cost.

For example:

```text
15K users with mostly text
```

could be substantially cheaper than:

```text
15K users uploading images/videos every day.
```

---

# 18. Metrics We Need to Track After Launch

The following metrics should be collected from day one:

### Users

- Total registered users

- DAU

- WAU

- MAU

- Active users / college

- Concurrent users

### API

- Requests/day

- Requests/sec

- Peak RPS

- Average response time

- P95 response time

- P99 response time

- Error rate

### Database

- Database size

- Queries/sec

- Slow queries

- Connections

- CPU

- Memory

- Storage growth

### Redis

- Memory usage

- Hit rate

- Commands/sec

- Evictions

### Storage

- Total media storage

- Storage growth/month

- Download bandwidth

- Upload bandwidth

### Application

- Posts/day

- Likes/day

- Comments/day

- Follows/day

- Notifications/day

- Messages/day

- Feed requests/day

---

# 19. Current Scale Target

For the first production version, Nexus should be designed around:

```text
30 Colleges
15,000 Students
600 Staff
30 College Admins
────────────────────
15,630 Registered Users
```

### Initial engineering target

```text
15K+ users
100+ peak RPS
1M+ interactions
10–20 GB+ database capacity
Hundreds of GB media capacity
Horizontal API scaling
Automated backups
Monitoring + logging
```

The architecture should be capable of growing toward:

```text
100K+ users
500+ RPS
10M+ interactions
TB-scale media storage
```

without requiring a complete rewrite.

---

# 20. Next Estimation Steps

The next version of this document should calculate:

- Exact DAU/MAU assumptions

- Requests per user

- Peak concurrent users

- Peak RPS

- Posts/day

- Likes/day

- Comments/day

- Follows/day

- Notifications/day

- Database rows/year

- Database storage/year

- Image storage/year

- Video storage/year

- Bandwidth/month

- Redis memory requirements

- Server CPU/RAM requirements

- PostgreSQL CPU/RAM/storage requirements

- Backup requirements

- Cloud provider comparison

- Monthly infrastructure cost

- Cost per 1,000 users

- Cost at 30K / 100K / 250K / 500K users

---

## Current Baseline

**Nexus initial scale: \~15,630 users across 30 colleges.**

The important point is that **15.6K users is not a particularly large scale for a modern backend**. The difficult part will likely be the *interaction and media workload* rather than the number of registered users itself.