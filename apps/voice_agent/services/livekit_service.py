"""
LiveKit management service.

Handles LiveKit room creation, SIP trunk configuration,
and agent dispatch for the self-hosted voice pipeline.
"""

import logging
import os

import requests
from django.conf import settings

logger = logging.getLogger("apps")


class LiveKitService:
    """Manage LiveKit rooms and SIP for the voice agent."""

    @staticmethod
    def _get_livekit_url():
        return getattr(settings, "LIVEKIT_URL", os.environ.get("LIVEKIT_URL", ""))

    @staticmethod
    def _get_api_credentials():
        return (
            getattr(settings, "LIVEKIT_API_KEY", os.environ.get("LIVEKIT_API_KEY", "")),
            getattr(settings, "LIVEKIT_API_SECRET", os.environ.get("LIVEKIT_API_SECRET", "")),
        )

    @classmethod
    def create_sip_trunk(cls, *, phone_number, website_id, provider="telnyx"):
        """
        Create a SIP inbound trunk in LiveKit for a phone number.

        This tells LiveKit to accept calls from the SIP provider
        and route them to the voice agent.
        """
        try:
            from livekit.api import LiveKitAPI, SIPInboundTrunkInfo

            api_key, api_secret = cls._get_api_credentials()
            api = LiveKitAPI(cls._get_livekit_url(), api_key, api_secret)

            trunk = SIPInboundTrunkInfo(
                name=f"voice-agent-{website_id}",
                numbers=[phone_number],
                metadata=f'{{"website_id": "{website_id}"}}',
            )

            result = api.sip.create_sip_inbound_trunk(trunk)
            logger.info(
                "sip_trunk_created",
                extra={"website_id": str(website_id), "phone": phone_number},
            )
            return result
        except ImportError:
            logger.warning("livekit-api package not installed")
            return None
        except Exception as e:
            logger.error("sip_trunk_creation_failed", extra={"error": str(e)})
            raise

    @classmethod
    def create_web_call_token(cls, *, website_id, user_id=""):
        """
        Generate a token for a browser-based voice call.

        The frontend uses this token to connect to LiveKit
        and speak with the voice agent directly from the browser.
        """
        try:
            from livekit.api import AccessToken, VideoGrant

            api_key, api_secret = cls._get_api_credentials()

            room_name = f"voice-agent-{website_id}-web"
            token = AccessToken(api_key, api_secret)
            token.identity = user_id or f"web-user-{website_id}"
            token.name = "Web Caller"
            token.metadata = f'{{"website_id": "{website_id}", "source": "web"}}'

            grant = VideoGrant(
                room_join=True,
                room=room_name,
            )
            token.add_grant(grant)

            return {
                "token": token.to_jwt(),
                "room": room_name,
                "livekit_url": cls._get_livekit_url(),
            }
        except ImportError:
            logger.warning("livekit-api package not installed")
            return None
        except Exception as e:
            logger.error("web_call_token_failed", extra={"error": str(e)})
            raise

    @classmethod
    def get_active_calls(cls):
        """List currently active LiveKit rooms (calls in progress)."""
        try:
            from livekit.api import LiveKitAPI

            api_key, api_secret = cls._get_api_credentials()
            api = LiveKitAPI(cls._get_livekit_url(), api_key, api_secret)

            rooms = api.room.list_rooms()
            return [
                {
                    "room_name": r.name,
                    "participants": r.num_participants,
                    "created_at": r.creation_time,
                    "metadata": r.metadata,
                }
                for r in rooms
                if r.name.startswith("voice-agent-")
            ]
        except Exception as e:
            logger.warning("list_active_calls_failed", extra={"error": str(e)})
            return []
