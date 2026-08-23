# Nexus — Scale & Cost Estimation

## 1. Current Scale

Nexus is planned for **30 colleges**, with **4 batches per college** and **500 students per batch**.

| User Type | Per College | 30 Colleges |
|---|---:|---:|
| Batches | 4 | 120 |
| Students | 2,000 | **60,000** |
| Staff / Faculty | 20 | **600** |
| College Admins | 1 | **30** |
| **Total Users** | **2,021** | **60,630** |

> **Initial production target: ~60.6K registered users**

---

## 2. Growth Targets

The architecture should scale without a major rewrite:

| Stage | Colleges | Approx. Users |
|---|---:|---:|
| MVP | 5 | ~10,105 |
| Initial Production | 30 | **~60,630** |
| Growth | 100 | ~202,100 |
| Large | 250 | ~505,250 |
| Very Large | 500 | ~1,010,500 |

---

## 3. Traffic Target

Registered users do not directly determine system load.

For the initial production deployment, target:

```text
60K+ registered users
15K–30K DAU
200–300 peak RPS
5M+ interaction records
```

The system should support horizontal API scaling toward:

```text
500+ RPS
```

as usage grows.

---

## 4. Database & Interaction Storage

Potential high-volume entities:

- Posts
- Likes
- Comments
- Follows
- Saves
- Views
- Notifications
- Messages
- Events
- User interactions

Use relational/junction tables rather than large arrays inside user or post records.

Example:

```text
likes
----------------
user_id
post_id
created_at

UNIQUE(user_id, post_id)
INDEX(user_id)
INDEX(post_id)
```

Initial PostgreSQL capacity target:

```text
20–50 GB+
```

with room for growth.

---

## 5. Media Storage

Media should **not** be stored inside PostgreSQL.

Use object storage for:

- Images
- Videos
- Documents
- Profile pictures
- Attachments

The system should support **hundreds of GB to TB-scale media storage** as Nexus grows.

---

## 6. Recommended Architecture

```text
Clients
   │
   ▼
Load Balancer / CDN
   │
   ▼
API Servers ───── Redis
   │
   ├──── PostgreSQL
   │
   ├──── Background Workers
   │
   └──── Object Storage
```

### Stack

| Component | Technology |
|---|---|
| API | FastAPI |
| Database | PostgreSQL |
| Cache | Redis |
| Object Storage | S3-compatible |
| Reverse Proxy / LB | Nginx / Cloud LB |
| Background Jobs | Celery / RQ |
| Search | PostgreSQL initially |
| Monitoring | Prometheus / Grafana or managed |
| CDN | CDN for media/static assets |

---

## 7. Initial Infrastructure

For ~60K users:

```text
2 API servers
1 PostgreSQL instance
1 Redis instance
Object storage
CDN
Background worker
Automated backups
Monitoring + centralized logs
```

Start simple and scale horizontally when actual traffic requires it.

---

## 8. Estimated Monthly Cost

Rough planning range for the initial 30-college deployment:

| Component | Monthly Estimate |
|---|---:|
| API / Compute | ₹5,000–₹12,000 |
| PostgreSQL | ₹3,000–₹8,000 |
| Redis | ₹1,000–₹3,000 |
| Object Storage | ₹1,000–₹6,000 |
| CDN / Bandwidth | ₹2,000–₹8,000 |
| Backups | ₹500–₹2,000 |
| Monitoring / Logs | ₹500–₹3,000 |
| **Total** | **₹13,000–₹42,000/month** |

Actual cost will depend mainly on **media usage, bandwidth, API traffic, and database workload**.

---

## 9. Scaling Strategy

### 0–100K Users

```text
Multiple API servers
PostgreSQL
Redis
Object storage
CDN
Background workers
```

Focus on:

- Indexing
- Pagination
- Caching
- Rate limiting
- Monitoring
- Backups

### 100K–500K Users

Introduce where required:

```text
Read replicas
Dedicated workers
Queue infrastructure
Dedicated search
Advanced caching
Database optimization
```

### 500K+ Users

Evaluate:

```text
Database sharding
Dedicated services
Distributed queues
Dedicated search infrastructure
Regional infrastructure
```

Do not introduce these systems until actual workload justifies them.

---

## 10. Key Metrics

Track from day one:

### Users
- Registered users
- DAU / WAU / MAU
- Concurrent users
- Active users per college

### API
- Requests/day
- Peak RPS
- P95 / P99 latency
- Error rate

### Database
- Size and growth
- Queries/sec
- Slow queries
- CPU / memory
- Connections

### Media
- Storage growth/month
- Upload bandwidth
- Download bandwidth

### Application
- Posts/day
- Likes/day
- Comments/day
- Follows/day
- Notifications/day
- Messages/day
- Feed requests/day

---

## 11. Current Engineering Target

```text
30 Colleges
60,000 Students
600 Staff
30 College Admins
────────────────────
60,630 Registered Users

Target:
200–300 peak RPS
5M+ interactions
20–50 GB+ database
TB-scale media capability
Horizontal API scaling
Automated backups
Monitoring + logging
```

> **The primary scaling challenge will be interaction and media workload, not the 60K user count itself.**