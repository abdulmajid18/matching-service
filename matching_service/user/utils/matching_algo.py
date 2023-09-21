import random
from django.db.models import Q
from enum import Enum

from ..models import CustomUser, Match, DeclinedMatch, MatchingCriteria, MatchRequest

MATCH_STATE_CHOICES = [
    ('Match', 'Match'),
    ('Unmatch', 'Unmatch'),
]


def update_match_state(sender, receiver):
    match = Match.objects.get(Q(user1=sender))
    match.user2 = receiver
    match.state = Match.MATCH_STATE_CHOICES[0][0]
    match.save()


def add_to_declined_matches(sender, receiver):
    declined_match = DeclinedMatch.objects.create(sender=sender, receiver=receiver)
    declined_match.save()


def update_individual_state(sender, receiver):
    update_match_state(sender, receiver)
    update_match_state(receiver, sender)


def create_or_update_matching_criteria(requested_user, min_age, max_age):
    matching_criteria, created = MatchingCriteria.objects.get_or_create(user=requested_user)
    matching_criteria.min_age = min_age
    matching_criteria.max_age = max_age
    matching_criteria.save()


def matching_algorithm(min_age, max_age, user):
    # Get the IDs of users who have declined match requests from actual_user
    users_declined_by_requested_user_ids = DeclinedMatch.objects.filter(
        sender=user
    ).values_list('sender_id', flat=True)

    # Get the IDs of users who have  requests declined by actual_user
    users_declining_requested_user_ids = DeclinedMatch.objects.filter(
        receiver=user
    ).values_list('receiver_id', flat=True)

    receiver_ids = DeclinedMatch.objects.filter(sender_id=user.id).values_list('receiver_id', flat=True)

    # Combine the two sets of IDs to exclude from the unmatched users queryset
    excluded_user_ids = set(users_declined_by_requested_user_ids) | set(users_declining_requested_user_ids) \
                                                                                                | set(receiver_ids)
    unmatched_users = CustomUser.objects.filter(
        Q(user1__state='Unmatch') | Q(user2__state='Unmatch'),
        age__gte=min_age,
        age__lte=max_age
    ).exclude(id=user.id).exclude(id__in=excluded_user_ids)

    return unmatched_users


def get_other_matched_user(user):
    match = Match.objects.filter(Q(user1=user) | Q(user2=user), state='Match').first()
    user2 = match.user2 if match.user1 == user else match.user1
    return user2