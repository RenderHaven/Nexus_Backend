import time
import uuid

import cloudinary
import cloudinary.api
import cloudinary.uploader
import cloudinary.utils

from app.config import settings

cloudinary.config(
    cloud_name=settings.CLOUDINARY_CLOUD_NAME,
    api_key=settings.CLOUDINARY_API_KEY,
    api_secret=settings.CLOUDINARY_API_SECRET,
    secure=True,
)

# The only folders anything may be uploaded into, keyed by what the upload is
# for. A caller names a purpose, never a path, so no request can reach outside
# these or into another folder.
MEDIA_PURPOSES: dict[str, str] = {
    "post": settings.POST_MEDIA_DIR,
    "profile": settings.PROFILE_MEDIA_DIR,
    "other": settings.OTHER_MEDIA_DIR,
}


class MediaService:

    # ------------------------------------------------------------------
    # Naming
    # ------------------------------------------------------------------

    @staticmethod
    def folder_for(purpose: str) -> str:
        """Resolve a purpose to its folder, falling back to the catch-all."""
        directory = MEDIA_PURPOSES.get(purpose, settings.OTHER_MEDIA_DIR)
        return f"{settings.MEDIA_BASE_DIR}/{directory}"

    @staticmethod
    def build_public_id(purpose: str, owner_id) -> str:
        """
        Mint the id an upload will be stored under.

        The server decides this, never the client: the folder comes from a
        fixed list, the owner is the authenticated user, and the leaf is
        random. That makes it impossible to aim an upload at somebody else's
        asset or at a folder outside the media root.
        """
        folder = MediaService.folder_for(purpose)
        return f"{folder}/{owner_id}/{uuid.uuid4().hex}"

    @staticmethod
    def _retarget(public_id: str, target_dir: str) -> str:
        """
        Point an existing public id at a different folder, keeping the owner
        and leaf so the asset stays traceable after it moves.
        """
        base = settings.MEDIA_BASE_DIR
        prefix = f"{base}/"

        tail = public_id[len(prefix):] if public_id.startswith(prefix) else public_id

        # Drop the current directory segment, keep everything after it.
        parts = tail.split("/", 1)
        remainder = parts[1] if len(parts) > 1 else parts[0]

        return f"{base}/{target_dir}/{remainder}"

    # ------------------------------------------------------------------
    # Upload
    # ------------------------------------------------------------------

    def get_signed_url(self, owner_id, purpose: str = "post") -> dict:
        """
        Sign a direct upload from the browser.

        The signature covers a server-chosen public_id, so the client can only
        upload to the one location we picked for it.

        max_file_size is returned for the uploader to honour. Cloudinary does
        not accept a size cap as a signed upload parameter, so enforcing it
        server-side means setting it on the Cloudinary upload preset; this
        value is what the preset should be configured to.
        """
        timestamp = int(time.time())
        public_id = self.build_public_id(purpose, owner_id)

        params = {
            "timestamp": timestamp,
            "tags": "temporary",
            "public_id": public_id,
        }

        signature = cloudinary.utils.api_sign_request(
            params_to_sign=params,
            api_secret=settings.CLOUDINARY_API_SECRET,
        )

        return {
            "signature": signature,
            "timestamp": timestamp,
            "public_id": public_id,
            "api_key": settings.CLOUDINARY_API_KEY,
            "cloud_name": settings.CLOUDINARY_CLOUD_NAME,
            "tags": "temporary",
            "max_file_size": settings.MAX_MEDIA_SIZE,
            "max_media_count": settings.MAX_MEDIA_COUNT,
        }

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def make_permanent(self, public_ids: list[str]) -> bool:
        """Media that made it onto a post is no longer a candidate for purging."""
        if not public_ids:
            return True
        try:
            cloudinary.uploader.remove_tag("temporary", public_ids)
            cloudinary.uploader.add_tag("permanent", public_ids)
            return True
        except Exception as e:
            print(f"Failed to make media permanent: {e}")
            return False

    def move_to_dir(self, public_ids: list[str], target_dir: str) -> list[str]:
        """
        Move assets into another folder, returning their new public ids.

        Used when a post is taken down: the files leave the live folder but
        are not destroyed, so a removal can still be reviewed afterwards.
        """
        if not public_ids:
            return []

        moved: list[str] = []

        for public_id in public_ids:
            new_public_id = self._retarget(public_id, target_dir)

            if new_public_id == public_id:
                continue

            try:
                cloudinary.uploader.rename(
                    public_id,
                    new_public_id,
                    overwrite=True,
                    invalidate=True,
                )
                moved.append(new_public_id)
            except Exception as e:
                print(f"Failed to move media {public_id}: {e}")

        return moved

    def move_to_deleted(self, public_ids: list[str]) -> list[str]:
        """Move a removed post's media out of the live folder."""
        return self.move_to_dir(public_ids, settings.DELETED_POST_MEDIA_DIR)

    def delete_media(self, public_ids: list[str]) -> bool:
        if not public_ids:
            return True
        try:
            cloudinary.api.delete_resources(public_ids)
            return True
        except Exception as e:
            print(f"Failed to delete media: {e}")
            return False
