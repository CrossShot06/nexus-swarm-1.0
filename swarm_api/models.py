from django.db import models

class MissionLog(models.Model):
    target_architecture = models.TextField()
    runtime_vectors = models.CharField(max_length=255, blank=True, null=True)
    blueprint = models.TextField()
    source_code = models.TextField()
    status = models.CharField(max_length=50) # 'SUCCESS' or 'FAILED'
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Mission [{self.created_at.strftime('%Y-%m-%d %H:%M:%S')}] - {self.status}"