"""Subject/body builders for account lifecycle emails.

Plain functions returning ``(subject, html)`` tuples. Inline HTML keeps
these self-contained — no template engine, no template directories, and
the copy is greppable next to the flows that send it. EmailService
derives the text/plain alternative from the HTML automatically.
"""
from django.conf import settings

_WRAPPER = """\
<div style="font-family:-apple-system,'Segoe UI',sans-serif;max-width:520px;margin:0 auto;padding:24px;color:#1a1816;">
  <p style="font-size:18px;font-weight:600;margin:0 0 16px;">Cansee</p>
  {body}
  <p style="font-size:12px;color:#6f6a60;margin-top:32px;">
    If you weren't expecting this email, you can safely ignore it.
  </p>
</div>"""


def _wrap(body: str) -> str:
    return _WRAPPER.format(body=body)


def verification_email(*, otp: str) -> tuple[str, str]:
    body = f"""\
  <p>Use this code to verify your email address:</p>
  <p style="font-size:28px;font-weight:700;letter-spacing:6px;margin:16px 0;">{otp}</p>
  <p>The code expires in 15 minutes.</p>"""
    return "Your Cansee verification code", _wrap(body)


def password_reset_email(*, token: str) -> tuple[str, str]:
    reset_url = f"{settings.FRONTEND_URL.rstrip('/')}/reset-password?token={token}"
    body = f"""\
  <p>Someone requested a password reset for your Cansee account.</p>
  <p style="margin:20px 0;">
    <a href="{reset_url}" style="background:#1a1816;color:#faf7f0;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">Reset password</a>
  </p>
  <p>This link expires in 1 hour. If the button doesn't work, paste this URL into your browser:</p>
  <p style="font-size:12px;word-break:break-all;color:#6f6a60;">{reset_url}</p>"""
    return "Reset your Cansee password", _wrap(body)


def org_invitation_email(
    *, org_name: str, inviter_name: str, role: str, token: str
) -> tuple[str, str]:
    accept_url = f"{settings.FRONTEND_URL.rstrip('/')}/invite/{token}"
    inviter = inviter_name or "A teammate"
    body = f"""\
  <p><strong>{inviter}</strong> invited you to join
  <strong>{org_name}</strong> on Cansee as a {role}.</p>
  <p>Cansee tracks how AI engines see your brand — you'll get access to
  {org_name}'s shared projects, dashboards, and knowledge base.</p>
  <p style="margin:20px 0;">
    <a href="{accept_url}" style="background:#1a1816;color:#faf7f0;padding:10px 20px;border-radius:8px;text-decoration:none;font-weight:600;">Accept invitation</a>
  </p>
  <p>This invitation expires in 7 days. If the button doesn't work, paste
  this URL into your browser:</p>
  <p style="font-size:12px;word-break:break-all;color:#6f6a60;">{accept_url}</p>"""
    return f"You're invited to {org_name} on Cansee", _wrap(body)
