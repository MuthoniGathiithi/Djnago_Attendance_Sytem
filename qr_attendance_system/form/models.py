from django.db import models

class Studentform(models.Model):
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=100)
    admin_no = models.CharField(max_length=20, null=True, blank=True)

    def __str__(self):
        return self.name
