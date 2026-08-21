# Stripe decommission: billing is Polar-managed.
# Hand-written so the invoice/event id columns are RENAMED (data kept)
# rather than dropped and recreated.
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("billing", "0007_alter_subscription_plan"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="subscription",
            name="stripe_customer_id",
        ),
        migrations.RemoveField(
            model_name="subscription",
            name="stripe_subscription_id",
        ),
        migrations.RenameField(
            model_name="invoice",
            old_name="stripe_invoice_id",
            new_name="external_invoice_id",
        ),
        migrations.RenameField(
            model_name="billingevent",
            old_name="stripe_event_id",
            new_name="event_id",
        ),
        migrations.DeleteModel(
            name="UsageRecord",
        ),
    ]
