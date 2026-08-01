# app/serializers/post_serializer.py

from app.db.model import Post


class PostSerializer:

    @staticmethod
    def to_dict(post: Post) -> dict:
        return {
            "id": str(post.id),
            "title": post.title,
            "body": post.body,

            "engagement_score": post.engagement_score,
            # "likes": post.likes,
            # "comments": post.comments,
            # "shares": post.shares,

            "created_at": (
                post.created_at.isoformat()
                if post.created_at
                else None
            ),

            "user_id": str(post.user_id),
            "category_id": str(post.category_id),

            "media": [
                {
                    "id": str(media.id),
                    "url": media.url,
                    "media_type": media.media_type.value,
                    "position": media.position,
                }
                for media in post.media
            ],
        }