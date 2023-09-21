from django.db import transaction
from django.db.models import Q
from drf_yasg.utils import swagger_auto_schema
from rest_framework import status, serializers
from rest_framework.decorators import action
from rest_framework.generics import RetrieveUpdateAPIView, CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ModelViewSet

from .models import Match, MatchRequest, MatchingCriteria, CustomUser
from .serializers import UserProfileSerializer, AgeRangeSerializer, MatchRequestSerializer

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


class MatchRequestCreateView(CreateAPIView):
    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated]

    def create_match_request(self, sender, receiver_id):
        match_request = MatchRequest()
        match_request.receiver = CustomUser.objects.get(pk=receiver_id)
        match_request.sender = sender
        match_request.save()
        return match_request

    def perform_create(self, serializer):
        sender = self.request.user
        receiver_id = self.kwargs.get('receiver_id')
        if sender.id == receiver_id:
            return Response({'message': 'Sender and receiver cannot be the same user'},
                            status=status.HTTP_400_BAD_REQUEST)
        request = self.create_match_request(sender=sender, receiver_id=receiver_id)
        serializer = MatchRequestSerializer(data=request)
        return Response({'message': 'Matching Request Successfully Sent to User', 'requests': serializer.data},
                        status=status.HTTP_201_CREATED)


class MatchRequestListView(ListAPIView):
    serializer_class = MatchRequestSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        receiver_id = self.request.user.id
        return MatchRequest.objects.filter(receiver_id=receiver_id)


class MatchRequestAcceptDeclineView(ModelViewSet):
    queryset = MatchRequest.objects.all()
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=['post'])
    def accept(self, request, pk):
        match_request = self.get_object()
        match_request.state = 'Accepted'
        match_request.save()
        sender = request.user
        receiver = match_request.receiver
        update_individual_state(sender, receiver)
        return Response({"message": "Match request accepted successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def decline(self, request, pk):
        match_request = self.get_object()
        match_request.state = 'Declined'
        match_request.save()
        sender = request.user
        receiver = match_request.receiver
        add_to_declined_matches(sender=sender, receiver=receiver)
        matching_criteria = MatchingCriteria.objects.get(user=sender)
        queryset = matching_algorithm(matching_criteria.min_age, matching_criteria.max_age, sender)
        serializer = UserProfileSerializer(queryset, many=True)
        return Response({'message': f'Match request declined by User {receiver}',
                         'possible_matches': serializer.data}, status=status.HTTP_200_OK)
