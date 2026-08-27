class RedisKeys:

    @staticmethod
    def post(post_id: str) -> str:
        return f"post:{post_id}"

    @staticmethod
    def user_liked_posts(user_id: str) -> str:
        return f"user:{user_id}:liked_posts"


    @staticmethod
    def post_comments(post_id: str) -> str:
        return f"post:{post_id}:comments"
    
    @staticmethod
    def feed(feed_id: str) -> str:
        return f"feed:{feed_id}"
    
    @staticmethod
    def pool(pool_name:str):
        return f"pool:{pool_name}"
    
    @staticmethod
    def category(category_id:str='all'):
        return f"category:{category_id}"

    @staticmethod
    def college(college_id: str = "all") -> str:
        return f"college:{college_id}"

    @staticmethod
    def user(user_id: str = "all") -> str:
        return f"user:{user_id}"

    @staticmethod
    def user_profile(user_id: str) -> str:
        return f"user:profile:{user_id}"
    
    @staticmethod
    def pool_cursor(id: str) -> str:
        return f"pool:cursor:{id}"

    @staticmethod
    def pool_group_cursor(id: str) -> str:
        return f"pool_group:cursor:{id}"

    @staticmethod
    def active_posts() -> str:
        return "post:all"

    @staticmethod
    def comment(comment_id: str) -> str:
        return f"comments:{comment_id}"
    
    @staticmethod
    def comment_replies(comment_id: str) -> str:
        return f"comments:replies:{comment_id}"

    @staticmethod
    def uploading_posts() -> str:
        return "post:uploading_posts"

    