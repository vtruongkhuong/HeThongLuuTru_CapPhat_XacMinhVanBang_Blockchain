from django.db import models
from django.conf import settings

class ReasonCode(models.Model):
    code = models.CharField(max_length=50, primary_key=True)
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.description

class RevocationRequest(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('EXECUTED', 'Executed'),
    ]

    degree = models.ForeignKey('degrees.Degree', on_delete=models.CASCADE, related_name='revocation_requests')
    reason_code = models.ForeignKey(ReasonCode, on_delete=models.PROTECT)
    description = models.TextField(null=True, blank=True)
    
    # Workflow 3 bước
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='requested_revocations')
    requested_at = models.DateTimeField(auto_now_add=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_revocations')
    approved_at = models.DateTimeField(null=True, blank=True)
    executed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='executed_revocations')
    executed_at = models.DateTimeField(null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')