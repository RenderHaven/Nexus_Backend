# Feed Builder API Contract

**OpenAPI:** `3.1.0`\
**API:** Feed Builder API\
**Version:** 1.0.0

> This document is generated from the supplied OpenAPI contract. It describes the currently defined HTTP endpoints, request parameters, response schemas, enums, and authentication scheme.

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

## 3. Endpoint Contract

### `POST /auth/login`

**Login Access Token**

OAuth2 compatible token login, get an access token for future requests

- **Operation ID:** `login_access_token_auth_login_post`
- **Authentication:** Not specified

#### Request Body

**Content-Type:** `application/x-www-form-urlencoded`\
**Schema:** `Body_login_access_token_auth_login_post`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Token` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /users/me`

**Get Me**

- **Operation ID:** `get_me_users_me_get`
- **Authentication:** Required

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `User` |

### `GET /users/my_post_items`

**Get My Post Items**

- **Operation ID:** `get_my_post_items_users_my_post_items_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `cursor` | `query` | string | null | No |
| `limit` | `query` | integer | No | `50` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /users/{user_id}`

**Get User**

- **Operation ID:** `get_user_users__user_id__get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `UserBasic` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /users/{user_id}/profile`

**Get Profile**

- **Operation ID:** `get_profile_users__user_id__profile_get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `User` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /users/{user_id}/post_items`

**Get Post Items**

- **Operation ID:** `get_post_items_users__user_id__post_items_get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `user_id` | `path` | string (uuid) | Yes | \`\` |
| `cursor` | `query` | string | null | No |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /users/me/profile`

**Update My Profile**

- **Operation ID:** `update_my_profile_users_me_profile_put`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** object

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `User` |
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
| `cursor` | `query` | string | null | No |
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
| `cursor` | `query` | string | null | No |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_UserPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/{college_id}`

**Get College**

- **Operation ID:** `get_college_colleges__college_id__get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `College` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /colleges/{college_id}/post_items`

**Get College Post Items**

- **Operation ID:** `get_college_post_items_colleges__college_id__post_items_get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `college_id` | `path` | string (uuid) | Yes | \`\` |
| `cursor` | `query` | string | null | No |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /categories`

**Get All Categories**

- **Operation ID:** `get_all_categories_categories_get`
- **Authentication:** Not specified

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `array<Category>` |

### `GET /categories/{category_id}`

**Get Category**

- **Operation ID:** `get_category_categories__category_id__get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `category_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Category` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /feeds/cursor`

**Get Feed Cursor**

- **Operation ID:** `get_feed_cursor_feeds_cursor_get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `cursor` | `query` | string | null | No |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /feeds/delete_cursor`

**Delete Feed Cursor**

- **Operation ID:** `delete_feed_cursor_feeds_delete_cursor_post`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `cursor` | `query` | string | null | No |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /feeds/groups`

**Get Feed Groups**

- **Operation ID:** `get_feed_groups_feeds_groups_get`
- **Authentication:** Not specified

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |

### `GET /feeds/post_items/{grp_name}`

**Get Feed Pool Members**

- **Operation ID:** `get_feed_pool_members_feeds_post_items__grp_name__get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `grp_name` | `path` | string | Yes | \`\` |
| `cursor` | `query` | string | null | No |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/`

**Add Post**

- **Operation ID:** `add_post_posts__post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `PostIdResponse` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/events`

**Add Event**

- **Operation ID:** `add_event_posts_events_post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `PostIdResponse` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/collaborations`

**Add Collaboration**

- **Operation ID:** `add_collaboration_posts_collaborations_post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `PostIdResponse` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/opportunities`

**Add Opportunity**

- **Operation ID:** `add_opportunity_posts_opportunities_post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostCreate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `PostIdResponse` |
| `422` | Validation Error | `HTTPValidationError` |

### `PUT /posts/{post_id}`

**Edit Post**

- **Operation ID:** `edit_post_posts__post_id__put`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | \`\` |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostUpdate`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `PostIdResponse` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/{post_id}`

**Get Post**

- **Operation ID:** `get_post_posts__post_id__get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Post` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/batch`

**Get Posts**

- **Operation ID:** `get_posts_posts_batch_post`
- **Authentication:** Required

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `PostIDsRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `array<Post>` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/{post_id}/comment_ids`

**Get Comment Ids**

- **Operation ID:** `get_comment_ids_posts__post_id__comment_ids_get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | \`\` |
| `cursor` | `query` | string | null | No |
| `limit` | `query` | integer | No | `20` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_UUID_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/comment`

**Comment Post**

- **Operation ID:** `comment_post_posts__post_id__comment_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | \`\` |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CommentRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/send_collab_request`

**Send Collab Request**

- **Operation ID:** `send_collab_request_posts__post_id__send_collab_request_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `CollabStatusResult` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/revoke_collab_request`

**Revoke Collab Request**

- **Operation ID:** `revoke_collab_request_posts__post_id__revoke_collab_request_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `CollabStatusResult` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/like`

**Like Post**

- **Operation ID:** `like_post_posts__post_id__like_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ReactionResult` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /posts/{post_id}/unlike`

**Unlike Post**

- **Operation ID:** `unlike_post_posts__post_id__unlike_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `ReactionResult` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /posts/type/{post_type}/post_items`

**Get Type Post Items**

- **Operation ID:** `get_type_post_items_posts_type__post_type__post_items_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `post_type` | `path` | `app__domains__types__enum__PostType` | Yes | \`\` |
| `cursor` | `query` | string | null | No |
| `limit` | `query` | integer | No | `10` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_PostPoolMember_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /comments/batch`

**Get Many Comments**

- **Operation ID:** `get_many_comments_comments_batch_post`
- **Authentication:** Not specified

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CommentIDsRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `array<Comment>` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /comments/{comment_id}`

**Get Comment**

- **Operation ID:** `get_comment_comments__comment_id__get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Comment` |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /comments/{comment_id}/reply_ids`

**Get Reply Ids**

- **Operation ID:** `get_reply_ids_comments__comment_id__reply_ids_get`
- **Authentication:** Not specified

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | \`\` |
| `cursor` | `query` | string | null | No |
| `limit` | `query` | integer | No | `20` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | `Paginated_UUID_` |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /comments/{comment_id}/reply`

**Comment Reply**

- **Operation ID:** `comment_reply_comments__comment_id__reply_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | \`\` |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CommentRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /comments/{comment_id}/edit`

**Edit Comment**

- **Operation ID:** `edit_comment_comments__comment_id__edit_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | \`\` |

#### Request Body

**Content-Type:** `application/json`\
**Schema:** `CommentRequest`

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |
| `422` | Validation Error | `HTTPValidationError` |

### `POST /comments/{comment_id}/delete`

**Delete Comment**

- **Operation ID:** `delete_comment_comments__comment_id__delete_post`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `comment_id` | `path` | string (uuid) | Yes | \`\` |

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |
| `422` | Validation Error | `HTTPValidationError` |

### `GET /media/signed_url`

**Get Signed Url**

Get a signature for uploading directly to Cloudinary from the frontend.

- **Operation ID:** `get_signed_url_media_signed_url_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `public_id` | `query` | string | null | No |
| `dir` | `query` | string | No | `other` |

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
| `200` | Successful Response | `array<ChatRoomSummary>` |

### `GET /chats/{chat_room_id}/msg_items`

**Get Chat Message Pool**

- **Operation ID:** `get_chat_message_pool_chats__chat_room_id__msg_items_get`
- **Authentication:** Required

#### Parameters

| Name | In | Type | Required | Default |
| --- | --- | --- | --- | --- |
| `chat_room_id` | `path` | string (uuid) | Yes | \`\` |
| `cursor` | `query` | string | null | No |
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
| `chat_room_id` | `path` | string (uuid) | Yes | \`\` |

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
- **Authentication:** Not specified

#### Responses

| Status | Description | Response Schema |
| --- | --- | --- |
| `200` | Successful Response | — |

## 4. Schemas

### `ActionStatus`

**Enum values:**

- `open`
- `closed`

### `Body_login_access_token_auth_login_post`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `grant_type` | string | null | No |
| `username` | string | Yes | — |
| `password` | string (password) | Yes | — |
| `scope` | string | No | default \`\` |
| `client_id` | string | null | No |
| `client_secret` | string | null | No |

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
| `name` | string | null | No |
| `status` | `ConversationStatus` | Yes | — |
| `created_at` | string (date-time) | Yes | — |

### `CollabStatusResult`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `status` | string | Yes | — |
| `collab_status` | `CollaborationRequestStatus` | Yes | — |
| `post_id` | string (uuid) | Yes | — |
| `user_id` | string (uuid) | Yes | — |

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
| `tagline` | string | null | No |
| `location` | string | null | No |
| `about` | string | null | No |
| `created_at` | string (date-time) | null | No |

### `Comment`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `post_id` | string (uuid) | Yes | — |
| `user_id` | string (uuid) | Yes | — |
| `body` | string | Yes | — |
| `parent_id` | string (uuid) | null | No |
| `reply_count` | integer | No | default `0` |
| `is_edited` | boolean | No | default `False` |
| `is_active` | boolean | No | default `True` |
| `created_at` | string (date-time) | null | No |
| `updated_at` | string (date-time) | null | No |

### `CommentIDsRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `comment_ids` | array&lt;string (uuid)&gt; | Yes | — |

### `CommentRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `comment` | string | Yes | maxLength `1000` |

### `ConversationStatus`

**Enum values:**

- `active`
- `closed`

### `Education`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `institution` | string | Yes | — |
| `degree` | string | null | No |
| `field_of_study` | string | null | No |
| `start_year` | integer | null | No |
| `end_year` | integer | null | No |

### `Experience`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `title` | string | Yes | — |
| `organisation` | string | Yes | — |
| `description` | string | null | No |
| `start_date` | string (date) | null | No |
| `end_date` | string (date) | null | No |
| `is_current` | boolean | No | default `False` |

### `HTTPValidationError`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `detail` | array&lt;`ValidationError`&gt; | No | — |

### `IdentityLevel`

**Enum values:**

- `spark`
- `kindler`
- `amplifier`
- `pathfinder`
- `horizon`
- `constellation`

### `JourneyMilestone`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `title` | string | Yes | — |
| `description` | string | null | No |
| `date` | string (date) | Yes | — |
| `icon` | string | null | No |

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
| `body` | string | null | No |
| `type` | `MessageType` | Yes | — |
| `created_at` | string (date-time) | Yes | — |

### `MessagePoolMember`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `chat_room_id` | string (uuid) | Yes | — |
| `sender_id` | string (uuid) | Yes | — |
| `body` | string | null | No |
| `type` | `MessageType` | Yes | — |
| `created_at` | string (date-time) | Yes | — |

### `MessageType`

**Enum values:**

- `text`
- `link`
- `file`

### `ModerationStatus`

**Enum values:**

- `pending`
- `approved`
- `hold`
- `removed`

### `Paginated_MessagePoolMember_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array&lt;`MessagePoolMember`&gt; | Yes | — |
| `next_cursor` | string | null | No |

### `Paginated_PostPoolMember_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array&lt;`PostPoolMember`&gt; | Yes | — |
| `next_cursor` | string | null | No |

### `Paginated_UUID_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array&lt;string (uuid)&gt; | Yes | — |
| `next_cursor` | string | null | No |

### `Paginated_UserPoolMember_`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `items` | array&lt;`UserPoolMember`&gt; | Yes | — |
| `next_cursor` | string | null | No |

### `Post`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `category_id` | string (uuid) | Yes | — |
| `type` | `PostType-Output` | No | default `spark` |
| `title` | string | null | No |
| `content` | string | Yes | — |
| `date_at` | string (date-time) | null | No |
| `restricted_to_college_id` | string (uuid) | null | No |
| `resources` | array&lt;`PostResource`&gt; | array | null |
| `action_status` | `ActionStatus` | null | No |
| `id` | string (uuid) | Yes | — |
| `user_id` | string (uuid) | Yes | — |
| `college_id` | string (uuid) | null | No |
| `status` | `PostStatus` | No | default `published` |
| `moderation_status` | `ModerationStatus` | No | default `pending` |
| `reviewed_by` | string (uuid) | null | No |
| `reviewed_at` | string (date-time) | null | No |
| `like_count` | integer | No | default `0` |
| `comment_count` | integer | No | default `0` |
| `save_count` | integer | No | default `0` |
| `engagement_score` | number | No | default `0` |
| `is_active` | boolean | No | default `True` |
| `created_at` | string (date-time) | Yes | — |
| `author` | `UserBasic` | null | No |
| `category` | `Category` | null | No |
| `collab_status` | `CollaborationRequestStatus` | null | No |
| `college` | `College` | null | No |
| `media` | array&lt;`PostMedia`&gt; | No | — |
| `is_liked` | boolean | null | No |

### `PostCreate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `category_id` | string (uuid) | Yes | — |
| `type` | `app__db__models__enums__PostType` | No | default `spark` |
| `title` | string | null | No |
| `content` | string | Yes | — |
| `date_at` | string (date-time) | null | No |
| `restricted_to_college_id` | string (uuid) | null | No |
| `resources` | array&lt;`PostResource`&gt; | array | null |
| `action_status` | `ActionStatus` | null | No |
| `media_ids` | array | No | — |

### `PostIDsRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `post_ids` | array&lt;string (uuid)&gt; | Yes | — |

### `PostIdResponse`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `post_id` | string (uuid) | Yes | — |
| `status` | string | null | No |
| `message` | string | null | No |

### `PostMedia`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `url` | string | Yes | — |
| `media_type` | `MediaType` | Yes | — |
| `position` | integer | Yes | — |

### `PostPoolMember`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `title` | string | null | No |
| `type` | `PostType-Output` | null | No |
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

### `PostType-Output`

**Enum values:**

- `achievement`
- `knowledge`
- `collaboration`
- `event`
- `opportunity`
- `spark`

### `PostUpdate`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `category_id` | string (uuid) | null | No |
| `type` | `app__db__models__enums__PostType` | null | No |
| `title` | string | null | No |
| `content` | string | null | No |
| `date_at` | string (date-time) | null | No |
| `restricted_to_college_id` | string (uuid) | null | No |
| `resources` | array&lt;`PostResource`&gt; | array | null |
| `action_status` | `ActionStatus` | null | No |
| `status` | `PostStatus` | null | No |
| `moderation_status` | `ModerationStatus` | null | No |
| `is_active` | boolean | null | No |
| `media_ids` | array | null | No |

### `Project`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `title` | string | Yes | — |
| `description` | string | null | No |
| `link` | string | null | No |
| `tech_stack` | array | null | No |

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

### `SendMessageRequest`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `body` | string | Yes | minLength `1`; maxLength `5000` |
| `type` | `MessageType` | No | default `text` |

### `SocialLink`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `title` | string | Yes | — |
| `link` | string | Yes | — |

### `Token`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `access_token` | string | Yes | — |
| `token_type` | string | Yes | — |

### `User`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `username` | string | Yes | — |
| `college_id` | string (uuid) | null | No |
| `role` | `UserRole` | Yes | — |
| `email` | string | null | No |
| `total_xp` | integer | No | default `0` |
| `current_level` | `IdentityLevel` | No | default `spark` |
| `profile` | `UserProfile` | No | — |
| `created_at` | string (date-time) | null | No |

### `UserBasic`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `username` | string | Yes | — |
| `college_id` | string (uuid) | null | No |
| `role` | `UserRole` | Yes | — |
| `email` | string | null | No |
| `total_xp` | integer | No | default `0` |
| `current_level` | `IdentityLevel` | No | default `spark` |

### `UserPoolMember`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `id` | string (uuid) | Yes | — |
| `username` | string | Yes | — |
| `college_id` | string (uuid) | Yes | — |
| `role` | `UserRole` | No | default `student` |

### `UserProfile`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `about` | string | null | No |
| `skills` | array | null | No |
| `social_links` | array&lt;`SocialLink`&gt; | null | No |
| `experience` | array&lt;`Experience`&gt; | null | No |
| `education` | array&lt;`Education`&gt; | null | No |
| `projects` | array&lt;`Project`&gt; | null | No |
| `journey` | array&lt;`JourneyMilestone`&gt; | null | No |

### `UserRole`

**Enum values:**

- `admin`
- `moderator`
- `success_coach`
- `student`
- `alumni`
- `guest`

### `ValidationError`

| Field | Type | Required | Default / Constraints |
| --- | --- | --- | --- |
| `loc` | array&lt;string | integer&gt; | Yes |
| `msg` | string | Yes | — |
| `type` | string | Yes | — |
| `input` | object | No | — |
| `ctx` | object | No | — |

### `app__db__models__enums__PostType`

**Enum values:**

- `achievement`
- `knowledge`
- `collaboration`
- `event`
- `opportunity`
- `spark`

### `app__domains__types__enum__PostType`

**Enum values:**

- `achievement`
- `knowledge`
- `spark`
- `opportunity`
- `event`
- `collaboration`

## 5. Security Scheme

### `OAuth2PasswordBearer`

- **Type:** OAuth2
- **Flow:** Password
- **Token URL:** `/auth/login`
- **Scopes:** None defined

## 6. Contract Notes

- The supplied OpenAPI document defines the HTTP contract; implementation-specific behavior not represented in the specification is intentionally not added here.
- Some response schemas are represented as empty inline objects in the supplied specification. Their concrete response fields therefore cannot be documented reliably from the contract alone.
- `PostType` appears twice in the supplied schemas under different generated names; both contain the same six logical post types, with ordering differences.