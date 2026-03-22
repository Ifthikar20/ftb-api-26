from django.urls import path

from . import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("refresh/", views.TokenRefreshView.as_view(), name="auth-refresh"),
    path("verify-email/", views.VerifyEmailView.as_view(), name="auth-verify-email"),
    path("resend-verification/", views.ResendVerificationView.as_view(), name="auth-resend-verification"),
    path("forgot-password/", views.ForgotPasswordView.as_view(), name="auth-forgot-password"),
    path("reset-password/", views.ResetPasswordView.as_view(), name="auth-reset-password"),
    path("change-password/", views.ChangePasswordView.as_view(), name="auth-change-password"),
    path("google/", views.GoogleOAuthView.as_view(), name="auth-google"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("me/export/", views.MeExportView.as_view(), name="auth-me-export"),
]
