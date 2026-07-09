from django.urls import path

from apps.billing.webhooks import stripe_webhook

from . import views
from .health import BillingHealthView

urlpatterns = [
    path("", views.BillingOverviewView.as_view(), name="billing-overview"),
    path("plans/", views.PlansView.as_view(), name="billing-plans"),
    path("checkout/", views.CheckoutView.as_view(), name="billing-checkout"),
    path("dev-subscribe/", views.DevSubscribeView.as_view(), name="billing-dev-subscribe"),
    path("cancel/", views.SubscriptionCancelView.as_view(), name="billing-cancel"),
    path("resume/", views.SubscriptionResumeView.as_view(), name="billing-resume"),
    path("portal/", views.PortalView.as_view(), name="billing-portal"),
    path("invoices/", views.InvoiceListView.as_view(), name="billing-invoices"),
    path("usage/", views.UsageView.as_view(), name="billing-usage"),
    path("token-usage/", views.AITokenUsageView.as_view(), name="billing-token-usage"),
    path("health/", BillingHealthView.as_view(), name="billing-health"),
    path("webhook/", stripe_webhook, name="billing-webhook"),
]
