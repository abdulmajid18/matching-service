from django.db import models
from django.contrib.auth.models import AbstractUser

GENDER_SELECTION = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('NS', 'Not Specified'),
]


class CustomUser(AbstractUser):
    # We don't need to define the email attribute because is inherited from AbstractUser
    gender = models.CharField(max_length=20, choices=GENDER_SELECTION)
    phone_number = models.CharField(max_length=30)
    age = models.PositiveIntegerField(null=True)


class Match(models.Model):
    MATCH_STATE_CHOICES = [
        ('Match', 'Match'),
        ('Unmatch', 'Unmatch'),
    ]

    user1 = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user1', null=True)
    user2 = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user2', null=True)
    state = models.CharField(max_length=7, choices=MATCH_STATE_CHOICES, default='Unmatch')

    def __str__(self):
        return f"{self.user1.username} - {self.user2.username} ({'Matched' if self.state else 'Not Matched'})"


class DeclinedMatch(models.Model):
    requesting_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='requested_declines')
    declined_user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_declines')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.requesting_user} declined a request from {self.declined_user}"
