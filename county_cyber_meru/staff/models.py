from django.db import models

# Create your models here.
from django.contrib.auth.models import AbstractUser

class StaffProfile(AbstractUser):
    RANK_CHOICES = (
        ('ADMIN', 'Administrator'),
        ('MANAGER', 'Manager'),
        ('STAFF', 'Regular Staff'),
    )

    rank = models.CharField(max_length=20, choices=RANK_CHOICES, default='STAFF')
    can_verify = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    department = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    profile_picture = models.ImageField(upload_to='staff_profiles/', blank=True, null=True)
    position = models.CharField(max_length=100, blank=True) 


    class Meta:
        verbose_name = 'Staff Profile'
        verbose_name_plural = 'Staff Profiles'

    def __str__(self):
        return f"{self.username} ({self.get_rank_display()})"