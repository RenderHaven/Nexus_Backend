class RedisKeys:

    @staticmethod
    def post(post_id: str) -> str:
        return f"post:{post_id}"
    
    @staticmethod
    def feed(feed_id: str) -> str:
        return f"feed:{feed_id}"
    
    @staticmethod
    def popular_feed():
        return f"feed:popular"