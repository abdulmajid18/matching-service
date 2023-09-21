from django.db import transaction
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Match, MatchRequest, MatchingCriteria, CustomUser
from .serializers import UserProfileSerializer, AgeRangeSerializer, MatchRequestSerializer, CustomUserSerializer

from .utils.matching_algo import matching_algorithm, update_individual_state, add_to_declined_matches, \
    create_or_update_matching_criteria


class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, ]

    def get_object(self):
        return self.request.user


class SuggestMatchesView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = AgeRangeSerializer

    def user_unmatched(self, user):
        # check if user is unmatched so we can suggest available users
        return Match.objects.filter(Q(user1=user) | Q(user2=user), state='Unmatch').exists()

    @swagger_auto_schema(
        request_body=AgeRangeSerializer,
        responses={200: UserProfileSerializer(many=True)}
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        requested_user = request.user

        # Check if the user already has a match
        user_in_match_record = Match.objects.filter(Q(user1=requested_user) | Q(user2=requested_user)).exists()

        if user_in_match_record:
            if not self.user_unmatched(requested_user):
                return Response({"detail": "You are currently matched"}, status=status.HTTP_200_OK)

        serializer = AgeRangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        min_age = serializer.validated_data.get("min_age")
        max_age = serializer.validated_data.get("max_age")

        create_or_update_matching_criteria(requested_user, min_age, max_age)

        queryset = matching_algorithm(min_age, max_age, requested_user)
        serializer = UserProfileSerializer(queryset, many=True)

        if not user_in_match_record:
            initialized_match = Match.objects.create(user1=requested_user)
            initialized_match.save()

        return Response({'possible_matches': serializer.data}, status=status.HTTP_201_CREATED)


class MatchRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic()
    def post(self, request, receiver_id, *args, **kwargs):
        sender = request.user
        if sender.id == receiver_id:
            return Response({'message': 'Sender and receiver cannot be the same user'},
                            status=status.HTTP_400_BAD_REQUEST)
        request = MatchRequest.create_match_request(sender=sender, receiver_id=receiver_id)
        response_data = {
            'message': 'Matching Request Successfully Sent to User',
            'state': 'Pending',
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class MatchRequestListView(ListAPIView):
    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        receiver_id = self.request.user.id
        return MatchRequest.objects.filter(receiver_id=receiver_id)


class MatchRequestAcceptDeclineView(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        match_request = MatchRequest.objects.get(receiver=user)
        return match_request

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def accept(self, request, sender_id):
        receiver = self.get_queryset()
        matched_user = CustomUser.objects.get(id=sender_id)
        match_request_state = receiver.matchrequeststate
        if match_request_state:
            match_request_state.state = 'Accepted'
            match_request_state.matched_user = matched_user
            match_request_state.save()
            update_individual_state(sender=matched_user, receiver=request.user)
            receiver.senders.remove(matched_user)
            return Response({"message": "Match request Accepted successfully"}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "User MatchState wasn't created"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def decline(self, request, sender_id):
        receiver = self.get_queryset()
        sender = CustomUser.objects.get(id=sender_id)
        receiver.senders.remove(sender)
        add_to_declined_matches(sender=sender, receiver=request.user)
        return Response({"message": "Match request Declined successfully"}, status=status.HTTP_200_OK)


class CheckRequestStatus(APIView):
    permission_classes = [IsAuthenticated]

    def has_sent_request_to_a_user(self, user):
        return MatchRequest.objects.filter(senders=user).exists()

    def get_request_receivers(self, known_sender):
        receiver_ids = MatchRequest.objects.filter(senders=known_sender).values_list('receiver_id', flat=True)
        receivers_queryset = CustomUser.objects.filter(pk__in=receiver_ids)
        return receivers_queryset

    def post(self, request, *args, **kwargs):
        user = request.user
        matching_criteria = MatchingCriteria.objects.get(user=user)
        pending_matches_queryset = matching_algorithm(matching_criteria.min_age, matching_criteria.max_age, user)
        possible_matches_serializer = UserProfileSerializer(pending_matches_queryset, many=True)
        try:
            match_request = MatchRequest.objects.get(senders=user)
            match_request_state = match_request.matchrequeststate
        except MatchRequest.DoesNotExist:
            match_request_state = None

        if match_request_state:
            if match_request_state.state == 'Accepted':
                return Response({
                    'message': f'Your request was accepted by User {match_request_state.matched_user}',
                    'possible matches still available': possible_matches_serializer.data
                }, status=status.HTTP_200_OK)

            else:
                pending_requests = self.get_request_receivers(user)
                pending_requests_serializer = CustomUserSerializer(pending_requests, many=True)
                pending_matches_queryset = pending_matches_queryset.exclude(
                    id__in=[user.id for user in pending_requests])
                possible_matches_serializer = UserProfileSerializer(pending_matches_queryset, many=True)
                return Response({
                    'message': 'Some of your requests are still pending',
                    'pending requests': pending_requests_serializer.data,
                    'possible_matches': possible_matches_serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({'message': 'No match found, Send a request to currently available matches',
                             'available matches': possible_matches_serializer.data},
                            status=status.HTTP_200_OK)
