import random
from django.db.models import Q
from enum import Enum

from ..models import CustomUser, Match, DeclinedMatch

MATCH_STATE_CHOICES = [
    ('Match', 'Match'),
    ('Unmatch', 'Unmatch'),
]


class InvitationStatus(Enum):
    ACCEPTED = 'Accepted'
    DECLINED = 'Declined'


def request_a_match(actual_user: CustomUser, targeted_user: CustomUser) -> str:
    # Simulate sending a request to the targeted user
    # status = send_request_to_targeted_user()
    status = InvitationStatus.ACCEPTED

    if status == InvitationStatus.ACCEPTED:
        # If the request is accepted, update the matches for both requested user and targeted users
        update_match_state(actual_user, targeted_user)
        update_match_state(targeted_user, actual_user)
        return "Request Accepted, Matched!"
    else:
        # If the request is declined make sure the previously selected user doesn't appear in the suggested matchers
        # If the request is declined, record the declined match request in the DeclinedMatch model
        declined_match = DeclinedMatch(requesting_user=actual_user, declined_user=targeted_user)
        declined_match.save()
        return "Request Declined, Select a different User"


def update_match_state(user1, user2):
    match = Match.objects.get(Q(user1=user1))
    match.user2 = user2
    match.state = Match.MATCH_STATE_CHOICES[0][0]
    match.save()


def send_request_to_targeted_user() -> MATCH_STATE_CHOICES:
    return random.choice(list(InvitationStatus))


def matching_algorithm(min_age, max_age, actual_user):
    # Get the IDs of users who have declined match requests from actual_user
    users_declined_by_requested_user_ids = DeclinedMatch.objects.filter(
        requesting_user=actual_user
    ).values_list('declined_user_id', flat=True)

    # Get the IDs of users who have  requests declined by actual_user
    users_declining_requested_user_ids = DeclinedMatch.objects.filter(
        declined_user=actual_user
    ).values_list('requesting_user_id', flat=True)

    # Combine the two sets of IDs to exclude from the unmatched users queryset
    excluded_user_ids = set(users_declined_by_requested_user_ids) | set(users_declining_requested_user_ids)
    unmatched_users = CustomUser.objects.filter(
        Q(user1__state='Unmatch') | Q(user2__state='Unmatch'),
        age__gte=min_age,
        age__lte=max_age
    ).exclude(id=actual_user.id).exclude(id__in=excluded_user_ids)

    return unmatched_users
