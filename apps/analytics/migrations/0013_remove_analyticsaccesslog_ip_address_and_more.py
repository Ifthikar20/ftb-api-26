"""Strip the personal data out of the analytics access trail.

AnalyticsAccessLog denormalized ``user_email``, ``ip_address`` and
``user_agent`` onto every row. It is the largest table in the database and
grows on every authenticated dashboard read, so it had become the single
biggest concentration of personal data we hold -- an email plus an IP per
page view, retained 90 days.

None of it was load-bearing. The audit property the table exists for --
proving that only the people who own a website ever read its analytics --
is carried by the ``user`` foreign key and ``accessed_at``. Identity is
resolved by joining at read time, which also means deleting a user removes
them from every historical row rather than leaving copies behind.

Dropping these columns is destructive and irreversible: the historical
email/IP/user-agent values are not recoverable afterwards. That is the
intent. The rows themselves, and the access trail they constitute, are
untouched.
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('analytics', '0012_analytics_access_log'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='analyticsaccesslog',
            name='ip_address',
        ),
        migrations.RemoveField(
            model_name='analyticsaccesslog',
            name='user_agent',
        ),
        migrations.RemoveField(
            model_name='analyticsaccesslog',
            name='user_email',
        ),
    ]
