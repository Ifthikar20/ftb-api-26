from django.urls import path
from . import views
from apps.billing.webhooks import stripe_webhook

urlpatterns = [
    path("", views.BillingOverviewView.as_view(), name="billing-overview"),
    path("plans/", views.PlansView.as_view(), name="billing-plans"),
    path("checkout/", views.CheckoutView.as_view(), name="billing-checkout"),
    path("portal/", views.PortalView.as_view(), name="billing-portal"),
    path("invoices/", views.InvoiceListView.as_view(), name="billing-invoices"),
    path("usage/", views.UsageView.as_view(), name="billing-usage"),
    path("webhook/", stripe_webhook, name="billing-webhook"),
]
