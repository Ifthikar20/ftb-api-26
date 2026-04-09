"""
LiveKit management service.

Handles LiveKit room creation, SIP trunk configuration,
and agent dispatch for the self-hosted voice pipeline.
"""

import logging
import os

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

    # ── Outbound calling ──────────────────────────────────────────────────

    @classmethod
    def create_outbound_sip_trunk(
        cls,
        *,
        name: str,
        telnyx_sip_address: str,
        sip_username: str,
        sip_password: str,
        from_number: str,
    ):
        """Register a LiveKit-side outbound SIP trunk pointed at Telnyx.

        Returns the trunk_id string. This is a one-time bootstrap per caller-ID
        number; the trunk_id is cached on PhoneNumber.livekit_outbound_trunk_id.
        """
        try:
            from livekit.api import LiveKitAPI, SIPOutboundTrunkInfo

            api_key, api_secret = cls._get_api_credentials()
            api = LiveKitAPI(cls._get_livekit_url(), api_key, api_secret)

            trunk = SIPOutboundTrunkInfo(
                name=name,
                address=telnyx_sip_address,
                numbers=[from_number],
                auth_username=sip_username,
                auth_password=sip_password,
            )
            result = api.sip.create_sip_outbound_trunk(trunk)
            trunk_id = getattr(result, "sip_trunk_id", None) or getattr(result, "id", "")
            logger.info(
                "outbound_sip_trunk_created",
                extra={"trunk_id": trunk_id, "from_number": from_number},
            )
            return trunk_id
        except ImportError:
            logger.warning("livekit-api package not installed")
            return None
        except Exception as e:
            logger.error(
                "outbound_sip_trunk_creation_failed", extra={"error": str(e)}
            )
            raise

    @classmethod
    def create_room(cls, *, name: str, metadata: str = ""):
        """Create (or no-op if exists) a LiveKit room with metadata for the worker."""
        try:
            from livekit.api import CreateRoomRequest, LiveKitAPI

            api_key, api_secret = cls._get_api_credentials()
            api = LiveKitAPI(cls._get_livekit_url(), api_key, api_secret)
            req = CreateRoomRequest(name=name, metadata=metadata, empty_timeout=300)
            return api.room.create_room(req)
        except ImportError:
            logger.warning("livekit-api package not installed")
            return None
        except Exception as e:
            logger.error("room_create_failed", extra={"room": name, "error": str(e)})
            raise

    @classmethod
    def dispatch_agent(cls, *, room_name: str, agent_name: str = "", metadata: str = ""):
        """Tell LiveKit to dispatch the named agent worker into the room."""
        try:
            from livekit.api import CreateAgentDispatchRequest, LiveKitAPI

            agent = agent_name or getattr(settings, "LIVEKIT_AGENT_NAME", "ftb-voice-agent")
            api_key, api_secret = cls._get_api_credentials()
            api = LiveKitAPI(cls._get_livekit_url(), api_key, api_secret)
            req = CreateAgentDispatchRequest(
                agent_name=agent, room=room_name, metadata=metadata
            )
            return api.agent_dispatch.create_dispatch(req)
        except ImportError:
            logger.warning("livekit-api package not installed")
            return None
        except Exception as e:
            logger.error("agent_dispatch_failed", extra={"room": room_name, "error": str(e)})
            raise

    @classmethod
    def create_sip_participant(
        cls,
        *,
        room_name: str,
        trunk_id: str,
        to_phone: str,
        from_phone: str,
        participant_identity: str = "",
        participant_name: str = "",
    ):
        """Place an outbound SIP call: LiveKit dials the recipient via the
        outbound trunk and bridges them into the room."""
        try:
            from livekit.api import CreateSIPParticipantRequest, LiveKitAPI

            api_key, api_secret = cls._get_api_credentials()
            api = LiveKitAPI(cls._get_livekit_url(), api_key, api_secret)
            req = CreateSIPParticipantRequest(
                sip_trunk_id=trunk_id,
                sip_call_to=to_phone,
                room_name=room_name,
                participant_identity=participant_identity or f"sip-{to_phone}",
                participant_name=participant_name or to_phone,
                sip_number=from_phone,
                play_dialtone=False,
            )
            result = api.sip.create_sip_participant(req)
            logger.info(
                "outbound_sip_participant_created",
                extra={
                    "room": room_name,
                    "to": to_phone,
                    "from": from_phone,
                    "trunk": trunk_id,
                },
            )
            return result
        except ImportError:
            logger.warning("livekit-api package not installed")
            return None
        except Exception as e:
            logger.error(
                "outbound_sip_participant_failed",
                extra={"room": room_name, "to": to_phone, "error": str(e)},
            )
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
