from django.db import models
from django.contrib.auth.models import User


class Analysis(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)


    job_title = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)

    cv_file = models.FileField(upload_to="uploads/cv/", blank=True, null=True)
    jd_file = models.FileField(upload_to="uploads/jd/", blank=True, null=True)

    cv_text = models.TextField()
    jd_text = models.TextField()

    match_percent = models.FloatField(null=True, blank=True)
    cv_keywords = models.JSONField(null=True, blank=True)
    jd_keywords = models.JSONField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Analysis by {self.user.username} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"