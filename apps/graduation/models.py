from django.db import models

class GraduationBatch(models.Model):
    name = models.CharField(max_length=150)
    decision_no = models.CharField(max_length=50, null=True, blank=True)
    decision_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return self.name