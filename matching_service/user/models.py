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


class MatchUsers(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='sender')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='receiver')

    def __str__(self):
        return f"{self.sender.username}  ' state is: Matched"


class MatchSuggestion(models.Model):
    MATCH_STATE_CHOICES = [
        ('Unmatched', 'Unmatched'),
        ('Pending', 'Pending'),
    ]
    user1 = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user1', null=True)
    user2 = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='user2', null=True)
    state = models.CharField(max_length=15, choices=MATCH_STATE_CHOICES, default='Unmatched')


class MatchingRequest(models.Model):
    REQUEST_STATE = [
        ('Accepted', 'Accepted'),
        ('Pending', 'Pending'),
        ('Declined', 'Declined'),
    ]
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='request_sender', null=True)
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='request_receiver', null=True)
    state = models.CharField(max_length=15, choices=REQUEST_STATE, default='Pending')

    def __str__(self):
        return f"Matching Request from {self.sender.username} to {self.receiver.username} (State: {self.state})"


class DeclinedMatch(models.Model):
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='requested_declines')
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_declines')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.receiver} declined a request from {self.sender}"
