# Feed Builder API Contract

**OpenAPI:** `3.1.0`\
**API:** Feed Builder API\
**Version:** 1.0.0

> This document is generated from the live FastAPI schema by
> `scripts/gen_api_contract.py`. Do not edit it by hand -- regenerate it after
> changing routes or response models.

## 1. Authentication

The API uses OAuth2 Password Bearer authentication.

- **Token endpoint:** `POST /auth/login`
- **Token flow:** OAuth2 password flow
- **Header for protected endpoints:** `Authorization: Bearer <access_token>`

### Login request

**Content-Type:** `application/x-www-form-urlencoded`

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `username` | string | Yes | Login username |
| `password` | string | Yes | Password |
| `grant_type` | string/null | No | If supplied, must be `password` |
| `scope` | string | No | Defaults to empty string |
| `client_id` | string/null | No | OAuth client id |
| `client_secret` | string/null | No | OAuth client secret |

**Response:** `Token`

```json
{
  "access_token": "string",
  "token_type": "string"
}
```

## 2. General Conventions

- IDs are UUID strings unless otherwise stated.
- Cursor-based endpoints accept an optional `cursor` query parameter.
- Paginated endpoints accept an optional `limit` query parameter.
- Validation failures are represented by HTTP `422` with `HTTPValidationError` where defined.
- Protected endpoints require OAuth2 Bearer authentication.
- Each endpoint states whether authentication is **Required**, **Optional**
  or **Not required**. *Optional* means a bearer token is read if supplied and
  enriches the response (for example `is_liked` on posts), but the request
  succeeds without one.
- Union types are written with `/`, so `string (uuid)/null` means a nullable
  UUID.

## 3. Endpoint Contract

### `POST /auth/login`

**Login Access Token**

OAuth2 compatible token login, get an access token for future requests

- **Operation ID:** `login_access_token_auth_login_post`
- **Authentication:** Not required

#### Request Body

**Content-Type:** `application/x-www-form-urlencoded`\
**Schema:** `Body_login_access_token_auth_login_post`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Token` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /admin/stats/overview`

**Get Overview**

The headline counters: members, colleges, posts, queue and who posted today.

Scoped to your own college unless you are an admin, who gets the platform-wide figures by default and one campus by passing college_id.

- **Operation ID:** `get_overview_admin_stats_overview_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `query` | string (uuid)/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Overview` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /admin/stats/posts_timeseries`

**Get Posts Timeseries**

Posts created, approved and removed per bucket.

Created counts by the day a post arrived; approved and removed count by the day the decision was made, so a backlog cleared on Friday shows on Friday. Buckets with no activity are absent rather than zero.

- **Operation ID:** `get_posts_timeseries_admin_stats_posts_timeseries_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `range` | `query` | `StatsRange` | No | `30d` |
| `interval` | `query` | `Interval` | No | `day` |
| `college_id` | `query` | string (uuid)/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `PostsBucket` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /admin/stats/users_timeseries`

**Get Users Timeseries**

Signups per bucket, optionally split by role.

- **Operation ID:** `get_users_timeseries_admin_stats_users_timeseries_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `range` | `query` | `StatsRange` | No | `30d` |
| `interval` | `query` | `Interval` | No | `day` |
| `split_by_role` | `query` | boolean | No | `false` |
| `college_id` | `query` | string (uuid)/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `UsersBucket` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /admin/stats/moderation`

**Get Moderation Stats**

Queue health: how much sits in each state, the median time to a decision, and how many decisions each moderator made.

The median is taken over posts actually decided in the range -- anything still waiting has no decision time and shows up in pending instead. Per-moderator figures come from the audit trail, which has no history before it started being written.

- **Operation ID:** `get_moderation_stats_admin_stats_moderation_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `range` | `query` | `StatsRange` | No | `30d` |
| `college_id` | `query` | string (uuid)/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ModerationStats` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /admin/stats/post_breakdown`

**Get Post Breakdown**

Publicly visible posts grouped by type, category or campus. Backs the donut and bar charts.

- **Operation ID:** `get_post_breakdown_admin_stats_post_breakdown_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `group_by` | `query` | `BreakdownBy` | No | `type` |
| `range` | `query` | `StatsRange` | No | `30d` |
| `college_id` | `query` | string (uuid)/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `BreakdownSlice` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /admin/stats/top_posts`

**Get Top Posts**

Best-performing content.

engagement orders by the stored score, which is not time-decayed -- an old post with a large score outranks a strong new one. Narrow the range to compare like with like.

- **Operation ID:** `get_top_posts_admin_stats_top_posts_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `metric` | `query` | `TopPostMetric` | No | `engagement` |
| `range` | `query` | `StatsRange` | No | `30d` |
| `limit` | `query` | integer | No | `10` |
| `college_id` | `query` | string (uuid)/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `TopPost` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /admin/stats/top_users`

**Get Top Users**

Most active contributors. Both post count and XP come back whichever one orders the list.

- **Operation ID:** `get_top_users_admin_stats_top_users_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `metric` | `query` | `TopUserMetric` | No | `posts` |
| `range` | `query` | `StatsRange` | No | `30d` |
| `limit` | `query` | integer | No | `10` |
| `college_id` | `query` | string (uuid)/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `TopUser` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /admin/stats/colleges`

**Get Colleges Rollup**

One row per college: members, posts and queue depth.

Uses the college domain's own counts, so this and the Manage-Colleges table can never disagree.

- **Operation ID:** `get_colleges_rollup_admin_stats_colleges_get`
- **Authentication:** Required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `CollegeRollup` |

### `GET /admin/activity`

**Get Activity**

Recent staff actions, newest first.

Post decisions only for now -- role changes and college edits join this once there is a general activity log. Scoped by the college of the post acted on, so an admin working on another campus appears in that campus's feed.

- **Operation ID:** `get_activity_admin_activity_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `limit` | `query` | integer | No | `50` |
| `offset` | `query` | integer | No | `0` |
| `college_id` | `query` | string (uuid)/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `ActivityEntry` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /home/trending_topics`

**Get Trending Topics**

What the platform is talking about right now, most active first.

- **Operation ID:** `get_trending_topics_home_trending_topics_get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `TrendingTopic` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /home/news`

**Get News**

Announcements for a college, newest first.

Defaults to your own college when you are signed in and no college is named.

- **Operation ID:** `get_news_home_news_get`
- **Authentication:** Optional (a bearer token enriches the response; omitting it still succeeds)

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `query` | string (uuid)/null | No | — |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `NewsItem` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /home/banners`

**Get Banners**

Campus banners for the top of the home screen.

Defaults to your own college when you are signed in and no college is named.

- **Operation ID:** `get_banners_home_banners_get`
- **Authentication:** Optional (a bearer token enriches the response; omitting it still succeeds)

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `query` | string (uuid)/null | No | — |
| `limit` | `query` | integer | No | `5` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `Banner` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /search`

**Get Search**

Search posts, people and colleges at once.

Results come back in three buckets, each always present. Narrow with scope to search only one kind of thing, or pass college_id to focus on one campus.

Signing in is optional; it only decides whether post hits come back with is_liked filled in.

- **Operation ID:** `get_search_search_get`
- **Authentication:** Optional (a bearer token enriches the response; omitting it still succeeds)

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `q` | `query` | string | Yes | — |
| `scope` | `query` | `SearchScope` | No | `all` |
| `college_id` | `query` | string (uuid)/null | No | — |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `SearchResult` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /users/me`

**Get Me**

Your own account and profile.

- **Operation ID:** `get_me_users_me_get`
- **Authentication:** Required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `User` |

### `GET /users/my_post_items`

**Get My Post Items**

Your posts that are visible to everyone.

Posts still awaiting review, held, or archived are listed separately by GET /posts/my_inactive_posts.

- **Operation ID:** `get_my_post_items_users_my_post_items_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `cursor` | `query` | string/null | No | — |
| `limit` | `query` | integer | No | `20` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /users/me/profile`

**Update My Profile**

Update your profile.

Only the fields you send are changed; anything you leave out keeps its current value. To clear a field, send it explicitly as null.

- **Operation ID:** `update_my_profile_users_me_profile_put`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `UserProfile`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_UserIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /users/`

**Add User**

Add someone to a college. Staff only.

An admin can add a user to any college; a moderator or success coach can only add one to their own college, and cannot hand out staff roles.

- **Operation ID:** `add_user_users__post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `UserCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `ApiResponse_UserIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /users/me/permissions`

**Get My Permissions**

What your account is allowed to do, and where.

Read straight off the permission tables, so the app can hide what you cannot use instead of guessing from your role name. college_id is the campus you are scoped to; an admin is platform-wide and scoped to none.

- **Operation ID:** `get_my_permissions_users_me_permissions_get`
- **Authentication:** Required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `MyPermissions` |

### `GET /users`

**List Users**

The user table. Staff only.

Narrow by college, role, alumni status, active state, or free text over username and email. A moderator or success coach is scoped to their own college: leave college_id out and it is filled in for you, and asking for another college is refused. An admin may ask for any, or omit it for all of them at once.

- **Operation ID:** `list_users_users_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `limit` | `query` | integer | No | `20` |
| `offset` | `query` | integer | No | `0` |
| `college_id` | `query` | string (uuid)/null | No | — |
| `role` | `query` | `UserRole`/null | No | — |
| `is_alumni` | `query` | boolean/null | No | — |
| `is_active` | `query` | boolean/null | No | — |
| `q` | `query` | string/null | No | — |
| `sort` | `query` | `UserSort` | No | `created_at` |
| `order` | `query` | `SortOrder` | No | `desc` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Page_UserAdminRow_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /users/bulk`

**Bulk User Action**

Apply one action to a selection of accounts. Staff only.

A refused id does not sink the batch: the response lists what went through and what did not, with a reason for each.

- **Operation ID:** `bulk_user_action_users_bulk_post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `BulkUserAction`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `BulkUserResult` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /users/{user_id}`

**Get User**

A person's public details.

- **Operation ID:** `get_user_users__user_id__get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `UserBasic` |
| `422` | Validation Error | `HTTPValidationError` |

### `PATCH /users/{user_id}`

**Update User**

Change someone's role, college or alumni status. Staff only.

A moderator or success coach may only edit members of their own college: not another staff account, and not to move someone elsewhere. Only an admin can do either.

- **Operation ID:** `update_user_users__user_id__patch`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `UserUpdate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_UserIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /users/{user_id}`

**Delete User**

Permanently delete an account. Admins only.

Refused with a conflict as soon as the person has written anything -- deleting an author would tear holes in other people's threads. Deactivate accounts with a history instead. You cannot delete your own account.

- **Operation ID:** `delete_user_users__user_id__delete`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_UserIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /users/{user_id}/deactivate`

**Deactivate User**

Take an account out of service. Staff only.

The person can no longer sign in, and everything they wrote is hidden from the feed and from search. Reversible, and the safe alternative to deleting someone. You cannot deactivate your own account.

- **Operation ID:** `deactivate_user_users__user_id__deactivate_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_UserIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /users/{user_id}/activate`

**Activate User**

Bring a deactivated account back. Staff only.

Their posts become visible again exactly as far as they were before: anything the author archived, or a moderator held, stays hidden.

- **Operation ID:** `activate_user_users__user_id__activate_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_UserIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /users/{user_id}/reset_password`

**Reset User Password**

Issue a temporary password. Admins only.

The password comes back once and is never readable again, so pass it on before closing the response. There is no email delivery yet.

- **Operation ID:** `reset_user_password_users__user_id__reset_password_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_TempPasswordPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /users/{user_id}/profile`

**Get Profile**

A person's public profile: their bio, skills, experience and journey.

- **Operation ID:** `get_profile_users__user_id__profile_get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `User` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /users/{user_id}/post_items`

**Get Post Items**

A person's publicly visible posts, newest first.

- **Operation ID:** `get_post_items_users__user_id__post_items_get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | — |
| `cursor` | `query` | string/null | No | — |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges`

**Get Colleges**

Every college on the platform, ordered by name.

Open to anyone: a signup flow needs it before there is a user to authenticate.

- **Operation ID:** `get_colleges_colleges_get`
- **Authentication:** Not required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `College` |

### `POST /colleges`

**Add College**

Create a college. Admins only.

- **Operation ID:** `add_college_colleges_post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CollegeCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `ApiResponse_CollegeIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/admin`

**List Colleges Admin**

The Manage-Colleges table. Staff only.

Each row carries its member, post and pending counts. An admin sees every college; a moderator or success coach sees the single row for their own.

Kept separate from GET /colleges, which stays the plain unpaginated list the signup flow reads before anyone is signed in.

- **Operation ID:** `list_colleges_admin_colleges_admin_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `limit` | `query` | integer | No | `20` |
| `offset` | `query` | integer | No | `0` |
| `q` | `query` | string/null | No | — |
| `sort` | `query` | `CollegeSort` | No | `name` |
| `order` | `query` | `SortOrder` | No | `asc` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Page_CollegeAdminRow_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/my_college`

**Get My College**

- **Operation ID:** `get_my_college_colleges_my_college_get`
- **Authentication:** Required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `College` |

### `GET /colleges/post_items`

**Get My College Post Items**

- **Operation ID:** `get_my_college_post_items_colleges_post_items_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `cursor` | `query` | string/null | No | — |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/user_items`

**Get My College Users**

- **Operation ID:** `get_my_college_users_colleges_user_items_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `cursor` | `query` | string/null | No | — |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_UserPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/{college_id}`

**Get College**

- **Operation ID:** `get_college_colleges__college_id__get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `College` |
| `422` | Validation Error | `HTTPValidationError` |

### `PATCH /colleges/{college_id}`

**Edit College**

Change a college's details. Staff only.

An admin can edit any college; a moderator or success coach can only edit their own. Only the fields you send are changed.

- **Operation ID:** `edit_college_colleges__college_id__patch`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CollegeUpdate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_CollegeIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /colleges/{college_id}`

**Delete College**

Permanently delete a college. Admins only.

Refused with a conflict while any member or post still belongs to it; the response says how many of each.

- **Operation ID:** `delete_college_colleges__college_id__delete`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_CollegeIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/{college_id}/stats`

**Get College Stats**

Headline numbers for one campus. Staff only, and own-campus only unless you are an admin.

active_this_week counts people who posted -- there is no last-seen signal yet, so it undercounts anyone who only reads.

- **Operation ID:** `get_college_stats_colleges__college_id__stats_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `CollegeStats` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/{college_id}/staff`

**Get College Staff**

Who moderates this campus. Staff only.

- **Operation ID:** `get_college_staff_colleges__college_id__staff_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `UserBasic` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/{college_id}/users`

**Get College People**

The people on one campus, newest first.

Backs the campus People tab and the alumni filter. Open to any signed-in user for any campus, the same way a public post is readable from anywhere. Deactivated accounts are left out.

- **Operation ID:** `get_college_people_colleges__college_id__users_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `path` | string (uuid) | Yes | — |
| `limit` | `query` | integer | No | `20` |
| `role` | `query` | `UserRole`/null | No | — |
| `is_alumni` | `query` | boolean/null | No | — |
| `q` | `query` | string/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `UserBasic` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/{college_id}/post_items`

**Get College Post Items**

- **Operation ID:** `get_college_post_items_colleges__college_id__post_items_get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `path` | string (uuid) | Yes | — |
| `cursor` | `query` | string/null | No | — |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /categories`

**Get All Categories**

- **Operation ID:** `get_all_categories_categories_get`
- **Authentication:** Not required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `Category` |

### `GET /categories/{category_id}`

**Get Category**

- **Operation ID:** `get_category_categories__category_id__get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `category_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Category` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /feeds/cursor`

**Get Feed Cursor**

- **Operation ID:** `get_feed_cursor_feeds_cursor_get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `cursor` | `query` | string/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /feeds/delete_cursor`

**Delete Feed Cursor**

- **Operation ID:** `delete_feed_cursor_feeds_delete_cursor_post`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `cursor` | `query` | string/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /feeds/groups`

**Get Feed Groups**

- **Operation ID:** `get_feed_groups_feeds_groups_get`
- **Authentication:** Not required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |

### `GET /feeds/post_items/{grp_name}`

**Get Feed Pool Members**

- **Operation ID:** `get_feed_pool_members_feeds_post_items__grp_name__get`
- **Authentication:** Optional (a bearer token enriches the response; omitting it still succeeds)

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `grp_name` | `path` | string | Yes | — |
| `cursor` | `query` | string/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/`

**Add Post**

Create a post.

New posts are held for review and are not visible to anyone else until a moderator approves them; the author can see their own the whole time. Event and opportunity posts may only be created by staff.

- **Operation ID:** `add_post_posts__post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `ApiResponse_PostIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/collaborations`

**Add Collaboration**

Create a collaboration post and open its chat room.

Other students can then ask to join, and the author decides who gets in. Like any post, it goes live once a moderator approves it.

- **Operation ID:** `add_collaboration_posts_collaborations_post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `ApiResponse_PostIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/events`

**Add Event**

Create an event post. Staff only.

Events are announcements for the whole campus, so they are limited to admins, moderators and success coaches, and are published under the college of the staff member creating them.

- **Operation ID:** `add_event_posts_events_post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `ApiResponse_PostIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/opportunities`

**Add Opportunity**

Create an opportunity post. Staff only.

Opportunities carry offers students may act on, so they are limited to admins, moderators and success coaches, and are published under the college of the staff member creating them.

- **Operation ID:** `add_opportunity_posts_opportunities_post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `ApiResponse_PostIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/batch`

**Get Posts**

Fetch several posts at once by id.

Feeds and listings return ids first, then load the posts they need in one call. Posts that are not public are skipped unless you are the author.

- **Operation ID:** `get_posts_posts_batch_post`
- **Authentication:** Optional (a bearer token enriches the response; omitting it still succeeds)

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostIDsRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `Post` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/my_inactive_posts`

**Get My Inactive Posts**

List your posts that are not public yet.

These are the posts waiting on review, held by a moderator, or archived by you, so you can track what has not gone live. Your published posts appear on your profile instead.

- **Operation ID:** `get_my_inactive_posts_posts_my_inactive_posts_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `limit` | `query` | integer | No | `20` |
| `offset` | `query` | integer | No | `0` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `Post` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/type/{post_type}/post_items`

**Get Type Post Items**

List posts of a single type, newest first.

Backs the dedicated tabs such as events, opportunities and collaborations. Pass the returned cursor to load the next page.

- **Operation ID:** `get_type_post_items_posts_type__post_type__post_items_get`
- **Authentication:** Optional (a bearer token enriches the response; omitting it still succeeds)

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_type` | `path` | `PostType` | Yes | — |
| `cursor` | `query` | string/null | No | — |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/moderation/counts`

**Get Moderation Counts**

How many posts sit in each moderation state. Staff only.

One call for every tab badge on the review screen. Scoped to your own college unless you are an admin, in which case college_id narrows it.

- **Operation ID:** `get_moderation_counts_posts_moderation_counts_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `query` | string (uuid)/null | No | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ModerationCounts` |
| `422` | Validation Error | `HTTPValidationError` |

### `PATCH /posts/moderation/bulk`

**Bulk Update Moderation**

Approve, hold or remove a selection of posts at once. Staff only.

One bad id does not sink the batch: the response lists what went through and what did not, with a reason for each failure.

- **Operation ID:** `bulk_update_moderation_posts_moderation_bulk_patch`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `BulkModerationUpdate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `BulkModerationResult` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/moderation/{moderation_status}`

**List Posts By Moderation Status**

Review queue for one moderation state. Staff only.

Use it to work through posts awaiting a decision, or to look back at what was approved, held or removed. Posts their author has archived or deleted are left out.

Narrow the queue by author, category, type, free text or a date range, and sort by when a post arrived, when it was reviewed, or how it is performing. A moderator is scoped to their own college: leave college_id out and it is filled in for you, and asking for another college is refused. An admin may ask for any, or omit it for all of them at once.

- **Operation ID:** `list_posts_by_moderation_status_posts_moderation__moderation_status__get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `moderation_status` | `path` | `ModerationStatus` | Yes | — |
| `limit` | `query` | integer | No | `20` |
| `offset` | `query` | integer | No | `0` |
| `college_id` | `query` | string (uuid)/null | No | — |
| `user_id` | `query` | string (uuid)/null | No | — |
| `category_id` | `query` | string (uuid)/null | No | — |
| `type` | `query` | `PostType`/null | No | — |
| `q` | `query` | string/null | No | — |
| `date_from` | `query` | string (date-time)/null | No | — |
| `date_to` | `query` | string (date-time)/null | No | — |
| `sort` | `query` | `ModerationSort` | No | `created_at` |
| `order` | `query` | `SortOrder` | No | `asc` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Page_Post_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/{post_id}/moderation_history`

**Get Moderation History**

Who decided what on this post, and when.

Readable by the post's author, so they can see why their post was held, by staff of that post's college, and by an admin.

- **Operation ID:** `get_moderation_history_posts__post_id__moderation_history_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `ModerationLogEntry` |
| `422` | Validation Error | `HTTPValidationError` |

### `PATCH /posts/{post_id}/moderation`

**Update Moderation Status**

Approve, hold or remove a post. Staff only.

Approving makes the post public; anything else keeps it hidden. A decision can be changed later -- staff may move a post between these states at any time -- and every change is recorded against whoever made it, with the note they left.

- **Operation ID:** `update_moderation_status_posts__post_id__moderation_patch`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `ModerationUpdate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_PostIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/{post_id}`

**Get Post**

Fetch a single post with its author, media and your own reaction state.

Returns not found for posts that are not public, unless you are the author.

- **Operation ID:** `get_post_posts__post_id__get`
- **Authentication:** Optional (a bearer token enriches the response; omitting it still succeeds)

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Post` |
| `422` | Validation Error | `HTTPValidationError` |

### `DELETE /posts/{post_id}`

**Delete Post Permanently**

Permanently delete a post. Staff only.

For content that must not remain on the platform at all. Authors removing their own posts should use the delete action instead, which is reversible on our side.

- **Operation ID:** `delete_post_permanently_posts__post_id__delete`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_PostIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/archive`

**Archive Post**

Archive your own post.

Takes the post out of public view without losing it; you can publish it again at any time.

- **Operation ID:** `archive_post_posts__post_id__archive_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_PostIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/publish`

**Publish Post**

Publish your own post again after archiving it.

It becomes visible again as soon as it is published, provided a moderator has already approved it.

- **Operation ID:** `publish_post_posts__post_id__publish_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_PostIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/delete`

**Delete Post**

Delete your own post.

Removes it from public view and from your listings. Only the author can delete their post.

- **Operation ID:** `delete_post_posts__post_id__delete_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_PostIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/{post_id}/comment_ids`

**Get Comment Ids**

List the ids of a post's top-level comments, newest first.

Ids come back first so the client can load only the comments it is about to show. Pass the returned cursor to load the next page.

- **Operation ID:** `get_comment_ids_posts__post_id__comment_ids_get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |
| `cursor` | `query` | string/null | No | — |
| `limit` | `query` | integer | No | `20` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_UUID_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/comment`

**Comment Post**

Add a comment to a post.

- **Operation ID:** `comment_post_posts__post_id__comment_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CommentRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `ApiResponse_CommentIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/like`

**Like Post**

Like a post.

Liking a post you already like changes nothing.

- **Operation ID:** `like_post_posts__post_id__like_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_ReactionResult_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/unlike`

**Unlike Post**

Remove your like from a post.

- **Operation ID:** `unlike_post_posts__post_id__unlike_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_ReactionResult_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /collabs/my_sent_requests`

**My Sent Requests**

Collaborations you have asked to join, and where each one stands.

Filter by status to see only the ones still waiting on the author, or only the ones you were accepted into.

- **Operation ID:** `my_sent_requests_collabs_my_sent_requests_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `status` | `query` | `CollaborationRequestStatus`/null | No | — |
| `limit` | `query` | integer | No | `20` |
| `offset` | `query` | integer | No | `0` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `CollabRequest` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /collabs/my_received_requests`

**My Received Requests**

People asking to join your collaborations, across all of your posts.

Filter by requested to work through the ones still waiting on you.

- **Operation ID:** `my_received_requests_collabs_my_received_requests_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `status` | `query` | `CollaborationRequestStatus`/null | No | — |
| `limit` | `query` | integer | No | `20` |
| `offset` | `query` | integer | No | `0` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `CollabRequest` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /collabs/requests/{request_id}/review`

**Review Request**

Accept or reject one request to join your collaboration.

Only the person the request was sent to can decide it. Accepting adds the sender to the post's chat room; rejecting is final and cannot be reopened.

- **Operation ID:** `review_request_collabs_requests__request_id__review_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `request_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CollabReviewRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_CollabStatusResult_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /collabs/{post_id}/request`

**Send Request**

Ask to join a collaboration post.

sender_id must be your own user id. The author of the post reviews the request and decides. Some collaborations are open only to one college; requests from outside it are refused, as are requests on your own post or ones you have already sent.

- **Operation ID:** `send_request_collabs__post_id__request_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CollabRequestCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `ApiResponse_CollabStatusResult_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /collabs/{post_id}/revoke`

**Revoke Request**

Withdraw a collaboration request you sent earlier.

sender_id must be your own user id. Withdrawing after being accepted also removes you from the chat room. You may ask to join again later.

- **Operation ID:** `revoke_request_collabs__post_id__revoke_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CollabRevokeRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_CollabStatusResult_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /collabs/{post_id}/requests`

**List Requests**

Who has asked to join one of your collaboration posts.

Only the author of the post can see this. Filter by status to work through the ones still waiting on a decision.

- **Operation ID:** `list_requests_collabs__post_id__requests_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | — |
| `status` | `query` | `CollaborationRequestStatus`/null | No | — |
| `limit` | `query` | integer | No | `20` |
| `offset` | `query` | integer | No | `0` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `CollabRequest` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /comments/batch`

**Get Many Comments**

Fetch several comments at once by id.

Listings return ids first, then load only the comments they are about to show.

- **Operation ID:** `get_many_comments_comments_batch_post`
- **Authentication:** Not required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CommentIDsRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `Comment` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /comments/{comment_id}`

**Get Comment**

A single comment.

- **Operation ID:** `get_comment_comments__comment_id__get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Comment` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /comments/{comment_id}/reply_ids`

**Get Reply Ids**

The ids of a comment's replies, newest first.

Pass the returned cursor to load the next page.

- **Operation ID:** `get_reply_ids_comments__comment_id__reply_ids_get`
- **Authentication:** Not required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | — |
| `cursor` | `query` | string/null | No | — |
| `limit` | `query` | integer | No | `20` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_UUID_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /comments/{comment_id}/reply`

**Comment Reply**

Reply to a comment.

- **Operation ID:** `comment_reply_comments__comment_id__reply_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CommentRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `ApiResponse_CommentIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /comments/{comment_id}/edit`

**Edit Comment**

Change the text of a comment you wrote.

The previous wording is kept, and the comment is marked as edited.

- **Operation ID:** `edit_comment_comments__comment_id__edit_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CommentRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_CommentIdPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /comments/{comment_id}/delete`

**Delete Comment**

Delete a comment you wrote.

Its replies go with it, so removed_count tells you how many comments disappeared in total.

- **Operation ID:** `delete_comment_comments__comment_id__delete_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | — |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ApiResponse_CommentDeletedPayload_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /media/signed_url`

**Get Signed Url**

Get everything needed to upload one file, plus the limits it must respect.

Say what the upload is for and the server decides where it goes and what it will be called; the returned public_id is the only location the signature is valid for. Send that same public_id back with the post so the file can be managed later.

max_file_size is the largest file accepted, and max_media_count is how many files one post may carry.

- **Operation ID:** `get_signed_url_media_signed_url_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `purpose` | `query` | string | No | `post` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /chats/my_chat_rooms`

**My Chat Rooms**

- **Operation ID:** `my_chat_rooms_chats_my_chat_rooms_get`
- **Authentication:** Required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | array of `ChatRoomSummary` |

### `GET /chats/{chat_room_id}/msg_items`

**Get Chat Message Pool**

- **Operation ID:** `get_chat_message_pool_chats__chat_room_id__msg_items_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `chat_room_id` | `path` | string (uuid) | Yes | — |
| `cursor` | `query` | string/null | No | — |
| `limit` | `query` | integer | No | `20` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_MessagePoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /chats/{chat_room_id}/message`

**Send Message**

- **Operation ID:** `send_message_chats__chat_room_id__message_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `chat_room_id` | `path` | string (uuid) | Yes | — |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `SendMessageRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `201` | Successful Response | `Message` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /`

**Root**

- **Operation ID:** `root__get`
- **Authentication:** Not required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |

## 4. Schemas

### `ActionStatus`

**Enum values:**

- `open`
- `closed`

### `ActivityEntry`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `action` | `ModerationAction` | Yes | — |
| `post_id` | string (uuid) | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `moderator_id` | string (uuid) | Yes | — |
| `moderator_username` | string/null | No | — |
| `note` | string/null | No | — |
| `created_at` | string (date-time) | Yes | — |

### `ApiResponse_CollabStatusResult_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | No | `success` |
| `message` | string/null | No | — |
| `payload` | `CollabStatusResult`/null | No | — |

### `ApiResponse_CollegeIdPayload_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | No | `success` |
| `message` | string/null | No | — |
| `payload` | `CollegeIdPayload`/null | No | — |

### `ApiResponse_CommentDeletedPayload_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | No | `success` |
| `message` | string/null | No | — |
| `payload` | `CommentDeletedPayload`/null | No | — |

### `ApiResponse_CommentIdPayload_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | No | `success` |
| `message` | string/null | No | — |
| `payload` | `CommentIdPayload`/null | No | — |

### `ApiResponse_PostIdPayload_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | No | `success` |
| `message` | string/null | No | — |
| `payload` | `PostIdPayload`/null | No | — |

### `ApiResponse_ReactionResult_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | No | `success` |
| `message` | string/null | No | — |
| `payload` | `ReactionResult`/null | No | — |

### `ApiResponse_TempPasswordPayload_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | No | `success` |
| `message` | string/null | No | — |
| `payload` | `TempPasswordPayload`/null | No | — |

### `ApiResponse_UserIdPayload_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | No | `success` |
| `message` | string/null | No | — |
| `payload` | `UserIdPayload`/null | No | — |

### `Banner`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `title` | string | Yes | — |
| `image_url` | string/null | No | — |
| `link` | string/null | No | — |
| `college_id` | string (uuid)/null | No | — |

### `Body_login_access_token_auth_login_post`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `grant_type` | string/null | No | — |
| `username` | string | Yes | — |
| `password` | string (password) | Yes | — |
| `scope` | string | No | \`\` |
| `client_id` | string/null | No | — |
| `client_secret` | string/null | No | — |

### `BreakdownBy`

**Enum values:**

- `type`
- `category`
- `college`

### `BreakdownSlice`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `key` | string | Yes | — |
| `label` | string/null | No | — |
| `count` | integer | No | `0` |

### `BulkModerationFailure`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `post_id` | string (uuid) | Yes | — |
| `reason` | string | Yes | — |

### `BulkModerationResult`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `updated` | array of string (uuid) | No | — |
| `failed` | array of `BulkModerationFailure` | No | — |

### `BulkModerationUpdate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `moderation_status` | `ModerationStatus` | Yes | — |
| `note` | string/null | No | — |
| `post_ids` | array of string (uuid) | Yes | — |

### `BulkUserAction`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `user_ids` | array of string (uuid) | Yes | — |
| `action` | `BulkUserActionType` | Yes | — |
| `value` | `UserRole`/null | No | — |

### `BulkUserActionType`

**Enum values:**

- `assign_role`
- `deactivate`
- `activate`

### `BulkUserFailure`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `user_id` | string (uuid) | Yes | — |
| `reason` | string | Yes | — |

### `BulkUserResult`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `updated` | array of string (uuid) | No | — |
| `failed` | array of `BulkUserFailure` | No | — |

### `Category`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `name` | string | Yes | — |

### `ChatRoomSummary`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `post_id` | string (uuid) | Yes | — |
| `name` | string/null | No | — |
| `status` | `ConversationStatus` | Yes | — |
| `created_at` | string (date-time) | Yes | — |

### `CollabRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `post_id` | string (uuid) | Yes | — |
| `sender_id` | string (uuid) | Yes | — |
| `recipient_id` | string (uuid) | Yes | — |
| `status` | `CollaborationRequestStatus` | Yes | — |
| `user_note` | string/null | No | — |
| `admin_note` | string/null | No | — |
| `created_at` | string (date-time) | Yes | — |
| `reviewed_at` | string (date-time)/null | No | — |
| `sender` | `UserMini`/null | No | — |
| `recipient` | `UserMini`/null | No | — |

### `CollabRequestCreate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `sender_id` | string (uuid) | Yes | — |
| `note` | string/null | No | — |

### `CollabReviewRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `accept` | boolean | Yes | — |
| `note` | string/null | No | — |

### `CollabRevokeRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `sender_id` | string (uuid) | Yes | — |

### `CollabStatusResult`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | Yes | — |
| `collab_status` | `CollaborationRequestStatus` | Yes | — |
| `request_id` | string (uuid)/null | No | — |
| `post_id` | string (uuid) | Yes | — |
| `sender_id` | string (uuid) | Yes | — |
| `recipient_id` | string (uuid)/null | No | — |

### `CollaborationRequestStatus`

**Enum values:**

- `requested`
- `accepted`
- `rejected`
- `revoked`

### `College`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `name` | string | Yes | — |
| `tagline` | string/null | No | — |
| `location` | string/null | No | — |
| `about` | string/null | No | — |
| `created_at` | string (date-time)/null | No | — |

### `CollegeAdminRow`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `name` | string | Yes | — |
| `tagline` | string/null | No | — |
| `location` | string/null | No | — |
| `about` | string/null | No | — |
| `created_at` | string (date-time)/null | No | — |
| `user_count` | integer | No | `0` |
| `post_count` | integer | No | `0` |
| `pending_count` | integer | No | `0` |

### `CollegeCreate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `name` | string | Yes | — |
| `tagline` | string/null | No | — |
| `location` | string/null | No | — |
| `about` | string/null | No | — |

### `CollegeIdPayload`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `college_id` | string (uuid) | Yes | — |

### `CollegeRollup`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `college_id` | string (uuid) | Yes | — |
| `name` | string | Yes | — |
| `users` | integer | No | `0` |
| `posts` | integer | No | `0` |
| `pending` | integer | No | `0` |

### `CollegeSort`

**Enum values:**

- `name`
- `created_at`

### `CollegeStats`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `users` | integer | No | `0` |
| `posts` | integer | No | `0` |
| `pending` | integer | No | `0` |
| `active_this_week` | integer | No | `0` |

### `CollegeUpdate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `name` | string/null | No | — |
| `tagline` | string/null | No | — |
| `location` | string/null | No | — |
| `about` | string/null | No | — |

### `Comment`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `post_id` | string (uuid) | Yes | — |
| `user_id` | string (uuid) | Yes | — |
| `body` | string | Yes | — |
| `parent_id` | string (uuid)/null | No | — |
| `reply_count` | integer | No | `0` |
| `is_edited` | boolean | No | `false` |
| `is_active` | boolean | No | `true` |
| `created_at` | string (date-time)/null | No | — |
| `updated_at` | string (date-time)/null | No | — |

### `CommentDeletedPayload`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `comment_id` | string (uuid) | Yes | — |
| `removed_count` | integer | Yes | — |

### `CommentIDsRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `comment_ids` | array of string (uuid) | Yes | — |

### `CommentIdPayload`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `comment_id` | string (uuid) | Yes | — |

### `CommentRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `comment` | string | Yes | — |

### `ConversationStatus`

**Enum values:**

- `active`
- `closed`

### `Education`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `institution` | string | Yes | — |
| `degree` | string/null | No | — |
| `field_of_study` | string/null | No | — |
| `start_year` | integer/null | No | — |
| `end_year` | integer/null | No | — |

### `Experience`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `title` | string | Yes | — |
| `organisation` | string | Yes | — |
| `description` | string/null | No | — |
| `start_date` | string (date)/null | No | — |
| `end_date` | string (date)/null | No | — |
| `is_current` | boolean | No | `false` |

### `HTTPValidationError`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `detail` | array of `ValidationError` | No | — |

### `IdentityLevel`

**Enum values:**

- `spark`
- `kindler`
- `amplifier`
- `pathfinder`
- `horizon`
- `constellation`

### `Interval`

**Enum values:**

- `day`
- `week`
- `month`

### `JourneyMilestone`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `title` | string | Yes | — |
| `description` | string/null | No | — |
| `date` | string (date) | Yes | — |
| `icon` | string/null | No | — |

### `MediaType`

**Enum values:**

- `image`
- `video`
- `gif`

### `Message`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `chat_room_id` | string (uuid) | Yes | — |
| `sender_id` | string (uuid) | Yes | — |
| `body` | string/null | No | — |
| `type` | `MessageType` | Yes | — |
| `created_at` | string (date-time) | Yes | — |

### `MessagePoolMember`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `chat_room_id` | string (uuid) | Yes | — |
| `sender_id` | string (uuid) | Yes | — |
| `body` | string/null | No | — |
| `type` | `MessageType` | Yes | — |
| `created_at` | string (date-time) | Yes | — |

### `MessageType`

**Enum values:**

- `text`
- `link`
- `file`

### `ModerationAction`

**Enum values:**

- `approve`
- `hold`
- `remove`

### `ModerationCounts`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `pending` | integer | No | `0` |
| `approved` | integer | No | `0` |
| `hold` | integer | No | `0` |
| `removed` | integer | No | `0` |

### `ModerationLogEntry`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `post_id` | string (uuid) | Yes | — |
| `action` | `ModerationAction` | Yes | — |
| `note` | string/null | No | — |
| `created_at` | string (date-time) | Yes | — |
| `moderator` | `UserBasic`/null | No | — |

### `ModerationSort`

**Enum values:**

- `created_at`
- `reviewed_at`
- `engagement`

### `ModerationStats`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `pending` | integer | No | `0` |
| `approved` | integer | No | `0` |
| `hold` | integer | No | `0` |
| `removed` | integer | No | `0` |
| `median_minutes_to_decision` | number/null | No | — |
| `by_moderator` | array of `ModeratorThroughput` | No | — |

### `ModerationStatus`

**Enum values:**

- `pending`
- `approved`
- `hold`
- `removed`

### `ModerationUpdate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `moderation_status` | `ModerationStatus` | Yes | — |
| `note` | string/null | No | — |

### `ModeratorThroughput`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `moderator_id` | string (uuid) | Yes | — |
| `username` | string/null | No | — |
| `decisions` | integer | No | `0` |

### `MyPermissions`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `user_id` | string (uuid) | Yes | — |
| `role` | `UserRole` | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `is_platform_wide` | boolean | No | `false` |
| `permissions` | array of string | No | — |

### `NewsItem`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `title` | string | Yes | — |
| `summary` | string/null | No | — |
| `link` | string/null | No | — |
| `image_url` | string/null | No | — |
| `college_id` | string (uuid)/null | No | — |
| `published_at` | string (date-time)/null | No | — |

### `Overview`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `users` | integer | No | `0` |
| `colleges` | integer | No | `0` |
| `posts` | integer | No | `0` |
| `pending` | integer | No | `0` |
| `active_today` | integer | No | `0` |

### `Page_CollegeAdminRow_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array of `CollegeAdminRow` | Yes | — |
| `total` | integer | Yes | — |
| `limit` | integer | Yes | — |
| `offset` | integer | Yes | — |

### `Page_Post_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array of `Post` | Yes | — |
| `total` | integer | Yes | — |
| `limit` | integer | Yes | — |
| `offset` | integer | Yes | — |

### `Page_UserAdminRow_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array of `UserAdminRow` | Yes | — |
| `total` | integer | Yes | — |
| `limit` | integer | Yes | — |
| `offset` | integer | Yes | — |

### `Paginated_MessagePoolMember_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array of `MessagePoolMember` | Yes | — |
| `next_cursor` | string/null | No | — |

### `Paginated_PostPoolMember_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array of `PostPoolMember` | Yes | — |
| `next_cursor` | string/null | No | — |

### `Paginated_UUID_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array of string (uuid) | Yes | — |
| `next_cursor` | string/null | No | — |

### `Paginated_UserPoolMember_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array of `UserPoolMember` | Yes | — |
| `next_cursor` | string/null | No | — |

### `Post`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `category_id` | string (uuid) | Yes | — |
| `type` | `PostType` | No | `spark` |
| `title` | string/null | No | — |
| `content` | string | Yes | — |
| `date_at` | string (date-time)/null | No | — |
| `restricted_to_college_id` | string (uuid)/null | No | — |
| `resources` | array of `PostResource`/null | No | — |
| `action_status` | `ActionStatus`/null | No | — |
| `id` | string (uuid) | Yes | — |
| `user_id` | string (uuid) | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `status` | `PostStatus` | No | `published` |
| `moderation_status` | `ModerationStatus` | No | `pending` |
| `reviewed_by` | string (uuid)/null | No | — |
| `reviewed_at` | string (date-time)/null | No | — |
| `like_count` | integer | No | `0` |
| `comment_count` | integer | No | `0` |
| `save_count` | integer | No | `0` |
| `engagement_score` | number | No | `0.0` |
| `is_active` | boolean | No | `true` |
| `created_at` | string (date-time) | Yes | — |
| `author` | `UserBasic`/null | No | — |
| `category` | `Category`/null | No | — |
| `collab_status` | `CollaborationRequestStatus`/null | No | — |
| `college` | `College`/null | No | — |
| `media` | array of `PostMedia` | No | — |
| `is_liked` | boolean/null | No | — |

### `PostBasic`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `title` | string/null | No | — |
| `type` | `PostType` | Yes | — |
| `content` | string | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `category_id` | string (uuid)/null | No | — |
| `like_count` | integer | No | `0` |
| `comment_count` | integer | No | `0` |
| `created_at` | string (date-time) | Yes | — |
| `author` | `UserBasic`/null | No | — |
| `is_liked` | boolean/null | No | — |

### `PostCreate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `category_id` | string (uuid) | Yes | — |
| `type` | `PostType` | No | `spark` |
| `title` | string/null | No | — |
| `content` | string | Yes | — |
| `date_at` | string (date-time)/null | No | — |
| `restricted_to_college_id` | string (uuid)/null | No | — |
| `resources` | array of `PostResource`/null | No | — |
| `action_status` | `ActionStatus`/null | No | — |
| `media` | array of `PostMediaInput` | No | — |

### `PostIDsRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `post_ids` | array of string (uuid) | Yes | — |

### `PostIdPayload`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `post_id` | string (uuid) | Yes | — |

### `PostMedia`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `url` | string | Yes | — |
| `public_id` | string/null | No | — |
| `type` | `MediaType` | Yes | — |
| `position` | integer | Yes | — |

### `PostMediaInput`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `public_id` | string | Yes | — |
| `url` | string | Yes | — |
| `type` | `MediaType` | Yes | — |

### `PostPoolMember`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `title` | string/null | No | — |
| `type` | `PostType`/null | No | — |
| `created_at` | string (date-time) | Yes | — |

### `PostResource`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `title` | string | Yes | — |
| `link` | string | Yes | — |

### `PostStatus`

**Enum values:**

- `published`
- `archived`
- `deleted`

### `PostType`

**Enum values:**

- `achievement`
- `knowledge`
- `collaboration`
- `event`
- `opportunity`
- `spark`

### `PostsBucket`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `bucket` | string (date) | Yes | — |
| `created` | integer | No | `0` |
| `approved` | integer | No | `0` |
| `removed` | integer | No | `0` |

### `Project`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `title` | string | Yes | — |
| `description` | string/null | No | — |
| `link` | string/null | No | — |
| `tech_stack` | array of string/null | No | — |

### `ReactionAction`

**Enum values:**

- `like.created`
- `like.deleted`

### `ReactionResult`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | Yes | — |
| `action` | `ReactionAction` | Yes | — |
| `post_id` | string (uuid) | Yes | — |
| `user_id` | string (uuid) | Yes | — |

### `SearchResult`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `query` | string | Yes | — |
| `posts` | array of `PostBasic` | No | — |
| `users` | array of `UserBasic` | No | — |
| `colleges` | array of `College` | No | — |

### `SearchScope`

**Enum values:**

- `all`
- `posts`
- `users`
- `colleges`

### `SendMessageRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `body` | string | Yes | — |
| `type` | `MessageType` | No | `text` |

### `SocialLink`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `title` | string | Yes | — |
| `link` | string | Yes | — |

### `SortOrder`

**Enum values:**

- `asc`
- `desc`

### `StatsRange`

**Enum values:**

- `7d`
- `30d`
- `90d`
- `1y`
- `all`

### `TempPasswordPayload`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `user_id` | string (uuid) | Yes | — |
| `temp_password` | string | Yes | — |

### `Token`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `access_token` | string | Yes | — |
| `token_type` | string | Yes | — |

### `TopPost`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `title` | string/null | No | — |
| `type` | `PostType` | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `user_id` | string (uuid) | Yes | — |
| `like_count` | integer | No | `0` |
| `comment_count` | integer | No | `0` |
| `engagement_score` | number | No | `0.0` |
| `created_at` | string (date-time) | Yes | — |

### `TopPostMetric`

**Enum values:**

- `engagement`
- `likes`
- `comments`

### `TopUser`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `username` | string | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `role` | `UserRole` | Yes | — |
| `total_xp` | integer | No | `0` |
| `post_count` | integer | No | `0` |

### `TopUserMetric`

**Enum values:**

- `posts`
- `xp`

### `TrendingTopic`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `name` | string | Yes | — |
| `post_count` | integer | No | `0` |
| `category_id` | string (uuid)/null | No | — |

### `User`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `username` | string | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `role` | `UserRole` | Yes | — |
| `is_alumni` | boolean | No | `false` |
| `total_xp` | integer | No | `0` |
| `current_level` | `IdentityLevel` | No | `spark` |
| `profile` | `UserProfile` | No | — |
| `created_at` | string (date-time)/null | No | — |

### `UserAdminRow`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `username` | string | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `role` | `UserRole` | Yes | — |
| `is_alumni` | boolean | No | `false` |
| `total_xp` | integer | No | `0` |
| `current_level` | `IdentityLevel` | No | `spark` |
| `email` | string | Yes | — |
| `is_active` | boolean | No | `true` |
| `created_at` | string (date-time)/null | No | — |
| `updated_at` | string (date-time)/null | No | — |

### `UserBasic`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `username` | string | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `role` | `UserRole` | Yes | — |
| `is_alumni` | boolean | No | `false` |
| `total_xp` | integer | No | `0` |
| `current_level` | `IdentityLevel` | No | `spark` |

### `UserCreate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `username` | string | Yes | — |
| `email` | string | Yes | — |
| `password` | string | Yes | — |
| `college_id` | string (uuid) | Yes | — |
| `role` | `UserRole` | No | `student` |
| `is_alumni` | boolean | No | `false` |

### `UserIdPayload`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `user_id` | string (uuid) | Yes | — |

### `UserMini`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `username` | string | Yes | — |
| `college_id` | string (uuid)/null | No | — |
| `role` | `UserRole` | Yes | — |

### `UserPoolMember`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `username` | string | Yes | — |
| `college_id` | string (uuid) | Yes | — |
| `role` | `UserRole` | No | `student` |
| `is_alumni` | boolean | No | `false` |
| `created_at` | string (date-time)/null | No | — |

### `UserProfile`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `about` | string/null | No | — |
| `skills` | array of string/null | No | — |
| `social_links` | array of `SocialLink`/null | No | — |
| `experience` | array of `Experience`/null | No | — |
| `education` | array of `Education`/null | No | — |
| `projects` | array of `Project`/null | No | — |
| `journey` | array of `JourneyMilestone`/null | No | — |

### `UserRole`

**Enum values:**

- `admin`
- `moderator`
- `success_coach`
- `student`
- `alumni`
- `guest`

### `UserSort`

**Enum values:**

- `created_at`
- `username`
- `role`
- `total_xp`

### `UserUpdate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `role` | `UserRole`/null | No | — |
| `college_id` | string (uuid)/null | No | — |
| `is_alumni` | boolean/null | No | — |

### `UsersBucket`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `bucket` | string (date) | Yes | — |
| `signups` | integer | No | `0` |
| `by_role` | object | No | — |

### `ValidationError`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `loc` | array of string/integer | Yes | — |
| `msg` | string | Yes | — |
| `type` | string | Yes | — |
| `input` | object | No | — |
| `ctx` | object | No | — |

## 5. Security Scheme

### `OAuth2PasswordBearer`

- **Type:** OAuth2
- **Flow:** Password
- **Token URL:** `/auth/login`
- **Scopes:** None defined

## 6. Contract Notes

- This document is generated from the live FastAPI schema; anything not
  expressible in OpenAPI is intentionally absent.
- `PostType` appears twice under different generated names; both contain the
  same six logical post types, with ordering differences.
- Search is backed by OpenSearch. Only publicly visible posts (`is_active`)
  are indexed, and `GET /search` forces that filter regardless of parameters,
  so hidden, held or archived posts never appear in results. An author's own
  hidden posts are served by `GET /posts/my_inactive_posts` instead.
- Search returns entity ids that are hydrated from the cache, so post and user
  objects in a search response carry the same fields they do everywhere else.
