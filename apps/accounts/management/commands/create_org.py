"""Provision an organization for a business customer.

The sales-assisted onboarding path while self-serve org creation stays
closed (SIGNUPS_ENABLED=False): creates the Organization, makes the named
existing user its owner-member, and optionally claims a domain (still
needs DNS TXT verification through the app before auto-join/SSO acts on
it).

    manage.py create_org --name "Acme Inc" --owner-email jane@acme.com \
        --domain acme.com --plan business
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify

from apps.accounts.models import Organization, OrganizationMember, OrgDomain, User
from core.utils.constants import OrgRole, Plan


class Command(BaseCommand):
    help = "Create an organization owned by an existing user."

    def add_arguments(self, parser):
        parser.add_argument("--name", required=True, help="Organization display name")
        parser.add_argument("--owner-email", required=True, help="Existing user who becomes owner")
        parser.add_argument("--slug", default="", help="URL slug (defaults to slugified name)")
        parser.add_argument("--plan", default=Plan.BUSINESS, help="Plan key (default: business)")
        parser.add_argument("--domain", default="", help="Company email domain to claim (unverified)")
        # The negotiated enterprise package. Omitted = plan defaults.
        parser.add_argument("--seats", type=int, default=None, help="Seat count sold (members + pending invites)")
        parser.add_argument("--monthly-prompts", type=int, default=None, help="Prompts per seat per month (-1 unlimited)")
        parser.add_argument("--prompts-per-audit", type=int, default=None, help="Prompt cap per single run")

    def handle(self, *args, **options):
        from django.conf import settings

        if not getattr(settings, "ORG_FEATURES_ENABLED", False):
            # Staging a customer before launch is legitimate — allow it,
            # but say loudly that nothing they were given works yet.
            self.stdout.write(self.style.WARNING(
                "ORG_FEATURES_ENABLED is off: the org will exist but every "
                "business flow (invites, SSO, org API) answers 404 until "
                "the flag is turned on."
            ))
        try:
            owner = User.objects.get(email__iexact=options["owner_email"].strip())
        except User.DoesNotExist:
            raise CommandError(
                f"No user with email {options['owner_email']!r}."
            ) from None

        if owner.org_memberships.exists():
            raise CommandError(f"{owner.email} already belongs to an organization.")

        valid_plans = {choice[0] for choice in Plan.choices}
        if options["plan"] not in valid_plans:
            raise CommandError(f"Unknown plan {options['plan']!r}. Choose from {sorted(valid_plans)}.")

        slug = slugify(options["slug"] or options["name"])[:80]
        if Organization.objects.filter(slug=slug).exists():
            raise CommandError(f"Slug {slug!r} is taken — pass --slug explicitly.")

        org = Organization.objects.create(
            name=options["name"].strip(),
            slug=slug,
            owner=owner,
            plan=options["plan"],
            seat_limit=options["seats"],
            monthly_prompt_allowance=options["monthly_prompts"],
            max_prompts_per_audit=options["prompts_per_audit"],
        )
        OrganizationMember.objects.create(
            organization=org,
            user=owner,
            role=OrgRole.OWNER,
            joined_via="founder",
        )

        # Existing personal projects move into the org so teammates see them.
        moved = owner.websites.filter(organization__isnull=True).update(organization=org)

        domain_note = ""
        if options["domain"]:
            record = OrgDomain(
                organization=org,
                domain=options["domain"],
                method="dns_txt",
                created_by=owner,
            )
            record.save()
            domain_note = (
                f"\nClaimed domain {record.domain} — have their IT add TXT "
                f"record at _cansee.{record.domain}: cansee-verification={record.dns_token}"
            )

        self.stdout.write(self.style.SUCCESS(
            f"Created org {org.name!r} (slug={org.slug}, plan={org.plan}) "
            f"owned by {owner.email}; moved {moved} project(s) into it.{domain_note}"
        ))
