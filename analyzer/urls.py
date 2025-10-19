from . import views
from django.contrib.auth.views import PasswordChangeView, PasswordChangeDoneView
from django.urls import path, reverse_lazy
urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("analysis_history/", views.analysis_history, name="analysis_history"),
    path("analysis/<int:pk>/", views.analysis_detail, name="analysis_detail"),
    path("analysis/<int:pk>/delete/", views.delete_analysis, name="analysis_delete"),
    # Auth
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout_view, name="logout"),
    path("account/password/", PasswordChangeView.as_view(
        template_name="registration/password_change_form.html",
        success_url=reverse_lazy("password_change_done"),
    ), name="password_change"),
    path("account/password/done/", PasswordChangeDoneView.as_view(
        template_name="registration/password_change_done.html",
    ), name="password_change_done"),
    path("account/", views.account_info, name="account"),
    path("account/delete/", views.delete_account, name="delete_account"),
]
