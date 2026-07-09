"""Brand Security agent framework.

Independent agents (each in ``services/security/agents/``) inspect the brand
across specific vectors: LLM answers, SERPs, Reddit / social, Google Trends,
and impersonation. Each agent's job is to catch a distinct class of narrative
risk before it goes unnoticed and to attribute every alert it raises back to
itself so the UI can show *what* was caught and *who* caught it.
"""
