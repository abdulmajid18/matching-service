from django.db.models import Q

from ..models import CustomUser, DeclinedMatch, MatchingCriteria, Match


def add_to_declined_matches(sender, receiver):
    declined_match = DeclinedMatch.objects.create(sender=sender, receiver=receiver)
    declined_match.save()


def create_or_update_matching_criteria(requested_user, min_age, max_age):
    matching_criteria, created = MatchingCriteria.objects.get_or_create(user=requested_user)
    matching_criteria.min_age = min_age
    matching_criteria.max_age = max_age
    matching_criteria.save()


def matching_algorithm(min_age, max_age, user):
    declined_request = DeclinedMatch.objects.filter(sender_id=user.id).values_list('receiver_id', flat=True)
    users_in_age_range = CustomUser.objects.filter(
        Q(user1__state='Unmatched'),
        age__gte=min_age,
        age__lte=max_age
    ).exclude(id=user.id).exclude(id__in=declined_request)
    return users_in_age_range
