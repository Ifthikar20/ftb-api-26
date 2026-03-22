"""
OpenClaw Gateway Service — communicates with the self-hosted OpenClaw AI agent.
Sends natural-language prompts to the OpenClaw /v1/responses endpoint
and parses structured lead data from the response.
"""
import json
import logging
import re

import requests
from django.conf import settings

logger = logging.getLogger("apps")

# Defaults (overridden by env vars in production)
DEFAULT_GATEWAY_URL = "http://localhost:18789"
DEFAULT_TIMEOUT = 90  # seconds — AI agents can take a while


class OpenClawService:
    """Client for the OpenClaw Gateway REST API."""

    @staticmethod
    def _gateway_url():
        return getattr(settings, "OPENCLAW_GATEWAY_URL", "") or DEFAULT_GATEWAY_URL

    @staticmethod
    def _auth_token():
        return getattr(settings, "OPENCLAW_AUTH_TOKEN", "") or ""

    @classmethod
    def is_available(cls) -> bool:
        """Check if the OpenClaw gateway is reachable."""
        try:
            resp = requests.get(
                f"{cls._gateway_url()}/health",
                timeout=5,
            )
            return resp.status_code == 200
        except Exception:
            return False

    @classmethod
    def send_prompt(cls, prompt: str, timeout: int = DEFAULT_TIMEOUT) -> dict | None:
        """
        Send a lead-finding prompt to the OpenClaw gateway.
        Returns parsed lead data dict, or None on failure.
        """
        gateway_url = cls._gateway_url()
        token = cls._auth_token()

        if not gateway_url:
            logger.debug("OpenClaw gateway URL not configured")
            return None

        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = f"Bearer {token}"

        # Build the request using OpenClaw's /v1/responses endpoint
        payload = {
            "model": "default",
            "input": (
                f"Use the fetchbot-leads skill to find leads matching this prompt. "
                f"Return ONLY the JSON result, no markdown or explanation.\n\n"
                f"Prompt: {prompt}"
            ),
            "instructions": (
                "You are a lead discovery agent. Use web search to find real people "
                "on X (Twitter) and LinkedIn who match the user's description. "
                "Return structured JSON with a 'leads' array. "
                "Each lead must have: name, title, company, email, phone, location, "
                "industry, linkedin_url, twitter_url, relevance_score, reason, source."
            ),
        }

        try:
            logger.info("OpenClaw request: %s -> %s", gateway_url, prompt[:80])
            resp = requests.post(
                f"{gateway_url}/v1/responses",
                headers=headers,
                json=payload,
                timeout=timeout,
            )

            if resp.status_code != 200:
                logger.warning(
                    "OpenClaw returned %d: %s", resp.status_code, resp.text[:200]
                )
                return None

            return cls._parse_response(resp.json())

        except requests.Timeout:
            logger.warning("OpenClaw request timed out after %ds", timeout)
            return None
        except requests.ConnectionError:
            logger.info("OpenClaw gateway not reachable at %s", gateway_url)
            return None
        except Exception as e:
            logger.error("OpenClaw request failed: %s", e)
            return None

    @staticmethod
    def _parse_response(response_data: dict) -> dict | None:
        """
        Extract structured lead data from an OpenClaw /v1/responses reply.
        The response may contain the JSON directly or wrapped in text.
        """
        try:
            # The response structure from /v1/responses has an 'output' array
            output_items = response_data.get("output", [])
            text_content = ""

            # Collect all text from the response
            for item in output_items:
                if isinstance(item, dict):
                    # Handle message-type items
                    content = item.get("content", "")
                    if isinstance(content, str):
                        text_content += content
                    elif isinstance(content, list):
                        for part in content:
                            if isinstance(part, dict) and part.get("type") == "text":
                                text_content += part.get("text", "")
                elif isinstance(item, str):
                    text_content += item

            # If output is empty, check for direct text in response
            if not text_content:
                text_content = response_data.get("text", "")
            if not text_content:
                text_content = json.dumps(response_data)

            # Try to extract JSON object with leads array
            json_obj_match = re.search(r"\{[^{}]*\"leads\"\s*:\s*\[.*?\]\s*[^{}]*\}", text_content, re.DOTALL)
            if json_obj_match:
                result = json.loads(json_obj_match.group())
                leads = result.get("leads", [])
                if leads:
                    # Normalize lead data
                    for lead in leads:
                        lead["relevance_score"] = int(lead.get("relevance_score", 50))
                        lead["is_from_search"] = bool(lead.get("is_from_search", True))
                        lead.setdefault("source", "openclaw")
                        lead.setdefault("email", "")
                        lead.setdefault("phone", "")
                    result["leads"] = sorted(
                        leads, key=lambda x: x["relevance_score"], reverse=True
                    )
                    return result

            # Try to extract just a JSON array of leads
            json_arr_match = re.search(r"\[.*\]", text_content, re.DOTALL)
            if json_arr_match:
                leads = json.loads(json_arr_match.group())
                if isinstance(leads, list) and len(leads) > 0:
                    for lead in leads:
                        lead["relevance_score"] = int(lead.get("relevance_score", 50))
                        lead["is_from_search"] = bool(lead.get("is_from_search", True))
                        lead.setdefault("source", "openclaw")
                        lead.setdefault("email", "")
                        lead.setdefault("phone", "")
                    return {
                        "leads": sorted(leads, key=lambda x: x["relevance_score"], reverse=True),
                        "sources_searched": {"x": 0, "linkedin": 0, "web": 0},
                        "criteria": {},
                    }

            logger.warning("Could not parse leads from OpenClaw response")
            return None

        except json.JSONDecodeError as e:
            logger.warning("JSON parse error from OpenClaw: %s", e)
            return None
        except Exception as e:
            logger.error("Failed to parse OpenClaw response: %s", e)
            return None
