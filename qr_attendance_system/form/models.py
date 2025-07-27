from django.db import models

class studentform(models.Models):
    name=models.CharField(max_length=100)
    course=models.CharField(max_length=100)
    adminno=models.CharField(max_length=100)

    def __str__(self):
     


# Create your models here.
