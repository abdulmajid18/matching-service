from django.db import transaction
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.generics import RetrieveUpdateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import MatchUsers, CustomUser, MatchingCriteria, MatchSuggestion, MatchingRequest
from .serializers import UserProfileSerializer, AgeRangeSerializer

from .utils.matching_algo import matching_algorithm, add_to_declined_matches, \
    create_or_update_matching_criteria


class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, ]

    def get_object(self):
        return self.request.user


class GetAMatch(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AgeRangeSerializer

    def is_user_in_match_suggestion(self, user):
        return MatchSuggestion.objects.filter(Q(user1=user)).exists()

    @swagger_auto_schema(
        request_body=AgeRangeSerializer,
        responses={200: UserProfileSerializer(many=True)}
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        matched_users = MatchUsers.objects.filter(Q(sender=user) | Q(receiver=user)).exists()
        if matched_users:
            return Response({'status': "Matched"}, status=status.HTTP_201_CREATED)
        serializer = AgeRangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        min_age = serializer.validated_data.get("min_age")
        max_age = serializer.validated_data.get("max_age")
        create_or_update_matching_criteria(user, min_age, max_age)
        queryset = matching_algorithm(min_age, max_age, user)
        matches_serializer = UserProfileSerializer(queryset, many=True)
        if self.is_user_in_match_suggestion(user=user):
            user_match = MatchSuggestion.objects.filter(Q(user1=user)).first()
            return Response({'Status': user_match.state, 'possible_matches': matches_serializer.data},
                            status=status.HTTP_201_CREATED)
        else:
            initialize_match = MatchSuggestion.objects.create(user1=user)
            initialize_match.save()
            return Response({'possible_matches': matches_serializer.data}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_match_status(request):
    user = request.user
    is_matched = MatchUsers.objects.filter(Q(sender=user) | Q(receiver=user)).exists()
    if is_matched:
        return Response({"status": "Matched", "detail": "You are currently Matched"}, status=status.HTTP_200_OK)
    try:
        match = MatchSuggestion.objects.get(Q(user1=user))
        user_status = match.state
    except MatchSuggestion.DoesNotExist:
        return Response({"detail": "You are currently No Available for Matching"}, status=status.HTTP_200_OK)
    criteria = MatchingCriteria.objects.get(user=user)
    queryset = matching_algorithm(criteria.min_age, criteria.max_age, user)
    serializer = UserProfileSerializer(queryset, many=True)
    return Response({'status': user_status, 'Possible Matches': serializer.data}, status=status.HTTP_200_OK)


class MatchRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def create_match_request(self, sender, receiver):
        matching_request = MatchingRequest.objects.create(
            sender=sender,
            receiver=receiver,
            state='Pending'
        )
        matching_request.save()
        return matching_request

    def update_match_request(self, sender, new_receiver):
        existing_request: MatchingRequest = MatchingRequest.objects.get(sender=sender)
        existing_request.receiver = new_receiver
        existing_request.state = 'Pending'
        existing_request.save()
        return existing_request

    def update_suggestion_state(self, sender, receiver):
        sender_suggestion: MatchSuggestion = MatchSuggestion.objects.get(user1=sender)
        sender_suggestion.user2 = receiver
        sender_suggestion.state = 'Pending'
        sender_suggestion.save()
        receiver_suggestion: MatchSuggestion = MatchSuggestion.objects.get(user1=receiver)
        receiver_suggestion.user2 = sender
        receiver_suggestion.state = 'Pending'
        receiver_suggestion.save()

    @transaction.atomic()
    def post(self, request, receiver_id, *args, **kwargs):
        sender = request.user
        receiver = CustomUser.objects.get(id=receiver_id)
        if sender.id == receiver_id:
            return Response({'message': 'Sender and receiver cannot be the same user'},
                            status=status.HTTP_400_BAD_REQUEST)
        user_exists_in_requests = MatchingRequest.objects.filter(sender=sender).exists()
        if user_exists_in_requests:
            matching_request = MatchingRequest.objects.get(sender=sender)
            if matching_request.state == 'Declined':
                self.update_suggestion_state(sender, receiver)
                updated_request = self.update_match_request(sender, receiver)
                state = updated_request.state
            else:
                state = matching_request.state
            response_data = {'state': state}
            return Response(response_data, status=status.HTTP_201_CREATED)

        self.update_suggestion_state(sender, receiver)
        match_request = self.create_match_request(sender, receiver)
        response_data = {
            'message': 'Matching Request Successfully Sent to User',
            'state': match_request.state,
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class MatchRequestListView(ListAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_match_requests(self, receiver, state):
        match_request = MatchingRequest.objects.filter(receiver=receiver, state=state).values_list('sender', flat=True)
        return CustomUser.objects.filter(id__in=match_request)

    def get_queryset(self):
        receiver = self.request.user
        state = 'Pending'
        requests = self.get_match_requests(receiver, state)
        return requests


class MatchRequestAcceptDeclineView(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_sender_request(self, sender):
        state = 'Pending'
        match_request = MatchingRequest.objects.get(sender=sender, state=state)
        return match_request

    def update_request_to_accepted(self, sender_request: MatchingRequest):
        sender_request.state = "Accepted"
        sender_request.save()
        receiver = self.request.user
        receiver_request = MatchingRequest.objects.filter(receiver=receiver).first()
        if receiver_request is not None:
            receiver_request.state = "Accepted"
            receiver_request.receiver = sender_request.sender
            receiver_request.save()

    def create_match(self, sender, receiver):
        MatchUsers.objects.create(sender=sender, receiver=receiver)

    def remove_users_from_suggestions(self, sender, receiver):
        sender_matching_suggestions = MatchSuggestion.objects.filter(user1=sender)
        sender_matching_suggestions.delete()
        receiver_matching_suggestions = MatchSuggestion.objects.filter(user1=receiver)
        receiver_matching_suggestions.delete()

    def update_state_to_unmatched(self, sender_request: MatchUsers, recipient):
        sender_request.state = 'Unmatched'
        sender_request.receiver = None
        sender_request.save()
        recipient_match = MatchUsers.objects.filter(user1=recipient).first()
        recipient_match.state = "Unmatched"
        recipient_match.receiver = None
        recipient_match.save()

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def accept(self, request, sender_id):
        sender = CustomUser.objects.get(id=sender_id)
        sender_match_request = self.get_sender_request(sender)
        self.update_request_to_accepted(sender_match_request)
        self.create_match(sender, request.user)
        self.remove_users_from_suggestions(sender, request.user)
        return Response({"message": "Match request Accepted successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def decline(self, request, sender_id):
        sender = CustomUser.objects.get(id=sender_id)
        add_to_declined_matches(sender=sender, receiver=request.user)
        sender_request = self.get_sender_request(sender_id)
        self.update_state_to_unmatched(sender_request, self.request.user)
        return Response({"message": "Match request Declined successfully"}, status=status.HTTP_200_OK)
