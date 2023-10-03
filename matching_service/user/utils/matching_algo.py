from ..models import DeclinedMatch, MatchingCriteria, MatchSuggestion, CustomUser


def add_to_declined_matches(sender, receiver):
    declined_match = DeclinedMatch.objects.create(sender=sender, receiver=receiver)
    declined_match.save()


def create_or_update_matching_criteria(requested_user, min_age, max_age):
    matching_criteria, created = MatchingCriteria.objects.get_or_create(user=requested_user)
    matching_criteria.min_age = min_age
    matching_criteria.max_age = max_age
    matching_criteria.save()


def matching_algorithm(min_age, max_age, user):
    decline_requests_by_receivers = DeclinedMatch.objects.filter(sender_id=user.id).values_list('receiver_id',
                                                                                                flat=True)
    decline_requests_by_sender = DeclinedMatch.objects.filter(receiver_id=user.id).values_list('sender_id', flat=True)
    excluded_user_ids = set(decline_requests_by_receivers) | set(decline_requests_by_sender) | {user.id}
    users_in_age_range = MatchSuggestion.objects.filter(
        state='Unmatched',
        user1__age__gte=min_age,
        user1__age__lte=max_age
    ).exclude(id__in=excluded_user_ids)
    user1_ids = users_in_age_range.values_list('user1', flat=True)
    custom_users_queryset = CustomUser.objects.filter(id__in=user1_ids)
    return custom_users_queryset
