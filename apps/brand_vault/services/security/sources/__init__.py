"""Shared source clients used by Brand Security agents.

Each module wraps one upstream (LLMs, Google SERP, Reddit, Google Trends,
X/Twitter, generic web) behind a small function or two. Agents call these
so multiple agents can share the same call surface without each one
reinventing rate-limiting, timeouts, and empty-payload handling.

Every source function must be tolerant of missing credentials and must
never raise on network errors -- return ``[]`` and let the agent decide
what to do.
"""
