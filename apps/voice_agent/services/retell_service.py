"""
Retell AI integration service.

Handles communication with Retell AI API for:
- Agent creation and configuration
- Phone number provisioning
- Call management
- Webhook signature verification
"""

import hashlib
import hmac
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger("apps")

RETELL_API_BASE = "https://api.retellai.com"


class RetellService:
    """Manage Retell AI voice agents and calls."""

    @staticmethod
    def _headers():
        return {
            "Authorization": f"Bearer {settings.RETELL_API_KEY}",
            "Content-Type": "application/json",
        }

    @classmethod
    def create_agent(cls, *, agent_name, system_prompt, greeting_message, voice_id="11labs-Adrian"):
        """Create a new voice agent in Retell AI."""
        payload = {
            "agent_name": agent_name,
            "response_engine": {
                "type": "retell-llm",
                "llm_id": None,
            },
            "voice_id": voice_id,
            "language": "en-US",
            "begin_message": greeting_message,
            "general_prompt": system_prompt,
            "general_tools": [
                {
                    "type": "custom",
                    "name": "schedule_appointment",
                    "description": (
                        "Schedule an appointment for the caller. "
                        "Use this when the caller wants to book a meeting or appointment."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "attendee_name": {
                                "type": "string",
                                "description": "Full name of the person booking",
                            },
                            "attendee_phone": {
                                "type": "string",
                                "description": "Phone number of the person booking",
                            },
                            "attendee_email": {
                                "type": "string",
                                "description": "Email address (optional)",
                            },
                            "preferred_date": {
                                "type": "string",
                                "description": "Preferred date in YYYY-MM-DD format",
                            },
                            "preferred_time": {
                                "type": "string",
                                "description": "Preferred time in HH:MM format (24h)",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for the appointment",
                            },
                        },
                        "required": ["attendee_name", "preferred_date", "preferred_time"],
                    },
                },
                {
                    "type": "custom",
                    "name": "request_callback",
                    "description": (
                        "Set a callback reminder when the caller wants to be called back later."
                    ),
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "contact_name": {
                                "type": "string",
                                "description": "Name of the person requesting callback",
                            },
                            "contact_phone": {
                                "type": "string",
                                "description": "Phone number to call back",
                            },
                            "preferred_time": {
                                "type": "string",
                                "description": "When to call back (e.g. 'tomorrow morning', '2024-03-15 14:00')",
                            },
                            "reason": {
                                "type": "string",
                                "description": "Reason for callback",
                            },
                        },
                        "required": ["contact_name", "contact_phone"],
                    },
                },
                {
                    "type": "custom",
                    "name": "check_availability",
                    "description": "Check available appointment slots for a given date.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "date": {
                                "type": "string",
                                "description": "Date to check in YYYY-MM-DD format",
                            },
                        },
                        "required": ["date"],
                    },
                },
            ],
        }

        resp = requests.post(
            f"{RETELL_API_BASE}/create-agent",
            headers=cls._headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def update_agent(cls, agent_id, **kwargs):
        """Update an existing Retell AI agent."""
        resp = requests.patch(
            f"{RETELL_API_BASE}/update-agent/{agent_id}",
            headers=cls._headers(),
            json=kwargs,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def delete_agent(cls, agent_id):
        """Delete a Retell AI agent."""
        resp = requests.delete(
            f"{RETELL_API_BASE}/delete-agent/{agent_id}",
            headers=cls._headers(),
            timeout=30,
        )
        resp.raise_for_status()

    @classmethod
    def get_phone_numbers(cls):
        """List available phone numbers."""
        resp = requests.get(
            f"{RETELL_API_BASE}/list-phone-numbers",
            headers=cls._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def purchase_phone_number(cls, *, area_code="", agent_id=""):
        """Purchase a new phone number and optionally bind to an agent."""
        payload = {}
        if area_code:
            payload["area_code"] = area_code
        if agent_id:
            payload["inbound_agent_id"] = agent_id
        resp = requests.post(
            f"{RETELL_API_BASE}/create-phone-number",
            headers=cls._headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def bind_phone_to_agent(cls, phone_number_id, agent_id):
        """Bind a phone number to an agent for inbound calls."""
        resp = requests.patch(
            f"{RETELL_API_BASE}/update-phone-number/{phone_number_id}",
            headers=cls._headers(),
            json={"inbound_agent_id": agent_id},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def get_call(cls, call_id):
        """Get details of a specific call."""
        resp = requests.get(
            f"{RETELL_API_BASE}/get-call/{call_id}",
            headers=cls._headers(),
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def list_calls(cls, *, agent_id="", limit=50):
        """List recent calls."""
        params = {"limit": limit}
        if agent_id:
            params["agent_id"] = agent_id
        resp = requests.get(
            f"{RETELL_API_BASE}/list-calls",
            headers=cls._headers(),
            params=params,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @classmethod
    def create_web_call(cls, agent_id, metadata=None):
        """Create a web-based call (browser-to-agent)."""
        payload = {"agent_id": agent_id}
        if metadata:
            payload["metadata"] = metadata
        resp = requests.post(
            f"{RETELL_API_BASE}/v2/create-web-call",
            headers=cls._headers(),
            json=payload,
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()

    @staticmethod
    def verify_webhook_signature(payload_body, signature, api_key):
        """Verify Retell webhook signature."""
        computed = hmac.new(
            api_key.encode("utf-8"),
            payload_body.encode("utf-8") if isinstance(payload_body, str) else payload_body,
            hashlib.sha256,
        ).hexdigest()
        return hmac.compare_digest(computed, signature)
