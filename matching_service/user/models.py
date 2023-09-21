from django.db import models
from django.contrib.auth.models import AbstractUser

GENDER_SELECTION = [
    ('M', 'Male'),
    ('F', 'Female'),
    ('NS', 'Not Specified'),
]


class CustomUser(AbstractUser):
    gender = models.CharField(max_length=20, choices=GENDER_SELECTION)
    phone_number = models.CharField(max_length=30)
    age = models.PositiveIntegerField(null=True)


class MatchingCriteria(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='matching_criteria')
    min_age = models.PositiveIntegerField(null=True)
    max_age = models.PositiveIntegerField(null=True)

    def __str__(self):
        return f"Matching Criteria for {self.user.username}"


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
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='requested_declines')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_declines')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sender} declined a request from {self.receiver}"


class MatchRequest(models.Model):
    REQUEST_STATE_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
        ('Declined', 'Declined'),
    ]

    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_requests')
    sender = models.ManyToManyField(CustomUser, related_name='sent_requests')
    state = models.CharField(max_length=10, choices=REQUEST_STATE_CHOICES, default='Pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.receiver.username}'s match request ({self.state})"
