import time
import cloudinary
import cloudinary.uploader
import cloudinary.api
import cloudinary.utils
from app.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

class MediaService:
    def get_signed_url(self, public_id: str = None, dir: str = "other") -> dict:
        """
        Generates a signature for the frontend to upload media to Cloudinary.
        By default, adds a 'temporary' tag so that unconfirmed uploads can be purged.
        """
        timestamp = int(time.time())
        folder = f"nexus_media/{dir}"
        params = {
            "timestamp": timestamp,
            "tags": "temporary",
            "folder": folder
        }
        if public_id:
            params["public_id"] = public_id

        signature = cloudinary.utils.api_sign_request(
            params_to_sign=params,
            api_secret=settings.CLOUDINARY_API_SECRET
        )
        return {
            "signature": signature,
            "timestamp": timestamp,
            "api_key": settings.CLOUDINARY_API_KEY,
            "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
            "tags": "temporary",
            "folder": folder
        }

    def make_permanent(self, public_ids: list[str]) -> bool:
        """Remove the 'temporary' tag from media items to make them permanent."""
        if not public_ids:
            return True
        try:
            # Add a 'permanent' tag and remove 'temporary' tag
            cloudinary.uploader.remove_tag("temporary", public_ids)
            cloudinary.uploader.add_tag("permanent", public_ids)
            return True
        except Exception as e:
            print(f"Failed to make media permanent: {e}")
            return False

    def delete_media(self, public_ids: list[str]) -> bool:
        if not public_ids:
            return True
        try:
            cloudinary.api.delete_resources(public_ids)
            return True
        except Exception as e:
            print(f"Failed to delete media: {e}")
            return False
