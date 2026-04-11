# Accounts App

## Purpose

Handles all authentication, user management, and organization/team features for FetchBot. This is the identity layer — every other app depends on it for user context and permissions.

## Architecture

```
Client (Vue frontend)
  │
  ├── POST /api/v1/auth/register/     → Create user + send verification OTP
  ├── POST /api/v1/auth/login/         → JWT token pair (access + refresh)
  ├── POST /api/v1/auth/verify-email/  → Validate 6-digit OTP
  └── POST /api/v1/auth/reset-password/→ Token-based password reset
         │
         ▼
   AuthService (services/)
         │
         ├── UserManager (custom manager, email-based auth)
         ├── Signals (post-save hooks for profile/preferences creation)
         └── Celery Tasks (async email sending, session cleanup)
```

## Models

| Model | Purpose |
|---|---|
| `User` | Custom user model with email-based auth. Tracks plan (Starter/Growth/Enterprise), segment, email verification status, and onboarding progress. Uses `AbstractBaseUser + PermissionsMixin`. |
| `Organization` | Enterprise billing entity. Has a slug, owner, and plan. Users belong to orgs via `OrganizationMember`. |
| `OrganizationMember` | M2M through model linking users to organizations with roles: owner, admin, member, viewer. |
| `UserProfile` | 1:1 extension for avatar, timezone, phone, bio. |
| `UserPreferences` | 1:1 preferences for email notifications, weekly reports, morning briefs. |
| `LoginAttempt` | SOC 2 audit trail — logs every login attempt (success/fail) with IP and user agent for brute-force detection. |
| `EmailVerificationOTP` | Short-lived 6-digit OTP for email verification. |
| `PasswordResetToken` | Secure 64-char token for password reset flow. |

## Key Design Decisions

- **Email-based auth** — no username. `USERNAME_FIELD = "email"`.
- **Plan inheritance** — `User.effective_plan` property checks org membership first, falling back to personal plan. Enterprise org members inherit the org's plan.
- **SOC 2 compliance** — `LoginAttempt` captures IP + user agent on every auth attempt for audit and rate-limiting.
- **Async email delivery** — OTP and password reset emails are sent via Celery tasks to avoid blocking the API response.

## Celery Tasks

| Task | Schedule | Purpose |
|---|---|---|
| `send_verification_email` | On-demand | Sends email verification OTP |
| `send_password_reset_email` | On-demand | Sends password reset token link |
| `expire_inactive_sessions` | Daily at 3 AM | Cleans up expired sessions |

## Dependencies

- **Depends on:** `core` (TimestampMixin, constants)
- **Depended on by:** Every other app (ForeignKey to `User`)
