from django.db import models
from django.contrib.auth.models import AbstractUser
import random
import string
from datetime import datetime, timedelta


class CustomUser(AbstractUser):
    phone_number = models.CharField(max_length=15, unique=True)
    is_2fa_enabled = models.BooleanField(default=True)
    is_phone_verified = models.BooleanField(default=False)
    
    def __str__(self):
        return self.username


class SMSToken(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    token = models.CharField(max_length=6)
    created_at = models.DateTimeField(auto_now_add=True)
    is_used = models.BooleanField(default=False)
    
    def is_expired(self):
        return datetime.now() > self.created_at + timedelta(minutes=5)
    
    def generate_token(self):
        self.token = ''.join(random.choices(string.digits, k=6))
        self.save()
        return self.token
    
    def __str__(self):
        return f"{self.user.username} - {self.token}"
