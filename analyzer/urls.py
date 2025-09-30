from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("about/", views.about, name="about"),
    path("analysis_history/", views.analysis_history, name="analysis_history"),
    path("analysis/<int:pk>/", views.analysis_detail, name="analysis_detail"),
    path("analysis/<int:pk>/delete/", views.delete_analysis, name="analysis_delete"),
]
