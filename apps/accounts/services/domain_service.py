"""Domain claiming and DNS TXT verification.

Verification model: claiming a domain writes an OrgDomain row with a random
``dns_token``; the customer's IT publishes ``cansee-verification=<token>``
as a TXT record at ``_cansee.<domain>``; the verify endpoint (and a daily
re-check task) resolves it. Only a verified domain can drive auto-join or
SSO enforcement — a Google ``hd`` claim alone never verifies (a defunct
domain's Workspace can be re-registered by anyone; a TXT record proves
present-day control).
"""
import logging

from django.utils import timezone

from apps.accounts.models import OrgDomain
from core.exceptions import CanseeException, ResourceNotFound
from core.logging.audit_logger import audit_log

logger = logging.getLogger("apps")

TXT_HOST_PREFIX = "_cansee"
TXT_VALUE_PREFIX = "cansee-verification="
# A verified domain loses verified status after this many consecutive
# failed re-checks (daily task => ~72h grace for DNS mishaps).
MAX_CONSECUTIVE_FAILURES = 3


def _lookup_txt_records(name: str) -> list[str]:
    """All TXT strings at ``name``. Empty on NXDOMAIN/timeouts; raises never."""
    try:
        import dns.resolver

        answers = dns.resolver.resolve(name, "TXT", lifetime=5.0)
        records = []
        for answer in answers:
            # dnspython splits >255-byte strings; join the fragments.
            records.append(
                "".join(
                    s.decode() if isinstance(s, bytes) else str(s)
                    for s in answer.strings
                )
            )
        return records
    except Exception:
        return []


class DomainService:
    @staticmethod
    def claim(*, acting, domain: str) -> OrgDomain:
        domain = (domain or "").strip().lower().rstrip(".")
        if OrgDomain.objects.filter(domain=domain).exists():
            raise CanseeException(
                "That domain is already claimed.",
                code="domain_claimed",
                status_code=409,
            )
        record = OrgDomain(
            organization=acting.organization,
            domain=domain,
            method="dns_txt",
            created_by=acting.user,
        )
        record.save()  # clean() validates format + freemail blocklist
        audit_log(
            "org.domain_claimed",
            user=acting.user,
            action="create",
            resource_type="org_domain",
            resource_id=str(record.id),
            metadata={"domain": record.domain},
        )
        return record

    @staticmethod
    def _get(acting, domain_id) -> OrgDomain:
        try:
            return OrgDomain.objects.get(
                id=domain_id, organization_id=acting.organization_id
            )
        except OrgDomain.DoesNotExist:
            raise ResourceNotFound("Domain not found.") from None

    @staticmethod
    def verify(*, acting, domain_id) -> tuple[OrgDomain, bool]:
        """Synchronous TXT check. Returns (domain, verified_now)."""
        record = DomainService._get(acting, domain_id)
        expected = f"{TXT_VALUE_PREFIX}{record.dns_token}"
        found = _lookup_txt_records(f"{TXT_HOST_PREFIX}.{record.domain}")
        record.last_checked_at = timezone.now()

        if expected in found:
            record.verified_at = record.verified_at or timezone.now()
            record.consecutive_failures = 0
            record.save(update_fields=[
                "verified_at", "consecutive_failures", "last_checked_at",
            ])
            audit_log(
                "org.domain_verified",
                user=acting.user,
                action="update",
                resource_type="org_domain",
                resource_id=str(record.id),
                metadata={"domain": record.domain},
            )
            return record, True

        record.save(update_fields=["last_checked_at"])
        return record, False

    @staticmethod
    def set_auto_join(*, acting, domain_id, enabled: bool) -> OrgDomain:
        record = DomainService._get(acting, domain_id)
        if enabled and not record.verified_at:
            raise CanseeException(
                "Verify the domain before enabling auto-join.",
                code="domain_not_verified",
                status_code=400,
            )
        record.auto_join = enabled
        record.save(update_fields=["auto_join"])
        return record

    @staticmethod
    def set_entra_tenant(*, acting, domain_id, tenant_id: str) -> OrgDomain:
        """Register (or clear) the Entra tenant that is authoritative for
        this domain. Empty string clears; anything else must be a GUID.
        """
        import uuid

        value = (tenant_id or "").strip().lower()
        if value:
            try:
                value = str(uuid.UUID(value))
            except (ValueError, AttributeError, TypeError):
                raise ValueError("Enter the Entra tenant ID as a GUID.") from None
        record = DomainService._get(acting, domain_id)
        record.entra_tenant_id = value
        record.save(update_fields=["entra_tenant_id"])
        audit_log(
            "org.domain_entra_tenant_set",
            user=acting.user,
            action="update",
            resource_type="org_domain",
            resource_id=str(record.id),
            metadata={"domain": record.domain, "entra_tenant_id": value},
        )
        return record

    @staticmethod
    def remove(*, acting, domain_id) -> None:
        record = DomainService._get(acting, domain_id)
        if acting.organization.require_sso and record.verified_at:
            others = acting.organization.domains.filter(
                verified_at__isnull=False
            ).exclude(id=record.id)
            if not others.exists():
                raise CanseeException(
                    "Disable SSO enforcement before removing the last verified domain.",
                    code="enforce_active",
                    status_code=400,
                )
        record.delete()

    @staticmethod
    def recheck_verified_domains() -> int:
        """Daily re-verification sweep; returns how many lost verification.

        A domain that expires or changes hands must not keep feeding
        auto-join. Three consecutive failures (~72h) clears verified_at,
        which freezes auto-join and blocks new SSO enforcement flips.
        """
        lost = 0
        for record in OrgDomain.objects.filter(
            verified_at__isnull=False, method="dns_txt"
        ).iterator():
            expected = f"{TXT_VALUE_PREFIX}{record.dns_token}"
            found = _lookup_txt_records(f"{TXT_HOST_PREFIX}.{record.domain}")
            record.last_checked_at = timezone.now()
            if expected in found:
                record.consecutive_failures = 0
                record.save(update_fields=["consecutive_failures", "last_checked_at"])
                continue
            record.consecutive_failures += 1
            update_fields = ["consecutive_failures", "last_checked_at"]
            if record.consecutive_failures >= MAX_CONSECUTIVE_FAILURES:
                record.verified_at = None
                update_fields.append("verified_at")
                lost += 1
                logger.warning(
                    "Org domain lost DNS verification: %s", record.domain
                )
            record.save(update_fields=update_fields)
        return lost
