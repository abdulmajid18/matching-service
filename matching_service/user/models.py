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
        return f"{self.receiver} declined a request from {self.sender}"


class MatchRequest(models.Model):
    receiver = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_requests')
    senders = models.ManyToManyField(CustomUser, related_name='sent_requests')

    def __str__(self):
        return f"{self.receiver.username}'s match request ({self.senders})"

    @classmethod
    def create_match_request(cls, sender, receiver_id):
        match_request = cls.objects.filter(receiver_id=receiver_id).first()

        if not match_request:
            match_request = cls(receiver_id=receiver_id)
            match_request.save()
            match_request_state = MatchRequestState.objects.create(match_request=match_request, state='Pending')
            match_request_state.save()

        match_request.senders.add(sender)
        return match_request


class MatchRequestState(models.Model):
    REQUEST_STATE_CHOICES = [
        ('Pending', 'Pending'),
        ('Accepted', 'Accepted'),
    ]

    match_request = models.OneToOneField(MatchRequest, on_delete=models.CASCADE)
    state = models.CharField(max_length=10, choices=REQUEST_STATE_CHOICES, default='Pending')
    matched_user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"State of MatchRequest for {self.match_request.receiver.username}"
