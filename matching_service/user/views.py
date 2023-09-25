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

from .models import Match, CustomUser, MatchingCriteria
from .serializers import UserProfileSerializer, AgeRangeSerializer, MatchRequestsSerializer

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

    def is_user_in_match_model(self, user):
        return Match.objects.filter(Q(user1=user)).exists()

    @swagger_auto_schema(
        request_body=AgeRangeSerializer,
        responses={200: UserProfileSerializer(many=True)}
    )
    @transaction.atomic
    def post(self, request, *args, **kwargs):
        user = request.user
        serializer = AgeRangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        min_age = serializer.validated_data.get("min_age")
        max_age = serializer.validated_data.get("max_age")
        create_or_update_matching_criteria(user, min_age, max_age)
        queryset = matching_algorithm(min_age, max_age, user)
        serializer = UserProfileSerializer(queryset, many=True)
        if self.is_user_in_match_model(user=user):
            user_match = Match.objects.filter(Q(user1=user)).first()
            return Response({'Status': user_match.state, 'possible_matches': serializer.data},
                            status=status.HTTP_201_CREATED)
        else:
            initialize_match = Match.objects.create(user1=user)
            initialize_match.save()
            return Response({'possible_matches': serializer.data}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_match_status(request):
    user = request.user
    try:
        match = Match.objects.get(Q(user1=user))
        user_status = match.state
    except Match.DoesNotExist:
        return Response({"detail": "You are currently No Available for Matching"}, status=status.HTTP_200_OK)
    criteria = MatchingCriteria.objects.get(user=user)
    queryset = matching_algorithm(criteria.min_age, criteria.max_age, user)
    serializer = UserProfileSerializer(queryset, many=True)
    return Response({'status': user_status, 'Possible Matches': serializer.data}, status=status.HTTP_200_OK)


class MatchRequestCreateView(APIView):
    permission_classes = [IsAuthenticated]

    def update_match(self, sender, recipient_id):
        recipient = CustomUser.objects.get(id=recipient_id)
        sender = Match.objects.filter(user1=sender).first()
        sender.state = "Pending"
        sender.user2 = recipient
        sender.save()
        recipient_match = Match.objects.filter(user1=recipient).first()
        recipient_match.state = "Pending"
        recipient_match.user2 = self.request.user
        recipient_match.save()



    @transaction.atomic()
    def post(self, request, receiver_id, *args, **kwargs):
        sender = request.user
        if sender.id == receiver_id:
            return Response({'message': 'Sender and receiver cannot be the same user'},
                            status=status.HTTP_400_BAD_REQUEST)
        self.update_match(sender, receiver_id)
        response_data = {
            'message': 'Matching Request Successfully Sent to User',
            'state': 'Pending',
        }
        return Response(response_data, status=status.HTTP_201_CREATED)


class MatchRequestListView(ListAPIView):
    serializer_class = MatchRequestsSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        recipient = self.request.user
        desired_state = 'Pending'
        match_requests_to_user2 = Match.objects.filter(user2=recipient, state=desired_state)
        return match_requests_to_user2


class MatchRequestAcceptDeclineView(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_sender_request(self, sender_id):
        user = self.request.user
        desired_state = 'Pending'
        match_request = Match.objects.filter(Q(user2=user) & Q(user1_id=sender_id), state=desired_state).first()
        return match_request

    def update_state_to_matched(self, sender_request: Match):
        sender_request.state = "Matched"
        sender_request.save()
        recipient = self.request.user
        recipient_request: Match = Match.objects.filter(user1=recipient).first()
        recipient_request.state = "Matched"
        recipient_request.user2 = sender_request.user1
        recipient_request.save()

    def update_state_to_unmatched(self, sender_request: Match, recipient):
        sender_request.state = 'Unmatched'
        sender_request.user2 = None
        sender_request.save()
        recipient_match = Match.objects.filter(user1=recipient).first()
        recipient_match.state = "Unmatched"
        recipient_match.user2 = None
        recipient_match.save()


    @action(detail=True, methods=['post'])
    @transaction.atomic
    def accept(self, request, sender_id):
        sender_match_request = self.get_sender_request(sender_id)
        self.update_state_to_matched(sender_match_request)
        return Response({"message": "Match request Accepted successfully"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def decline(self, request, sender_id):
        sender = CustomUser.objects.get(id=sender_id)
        add_to_declined_matches(sender=sender, receiver=request.user)
        sender_request = self.get_sender_request(sender_id)
        self.update_state_to_unmatched(sender_request, self.request.user)
        return Response({"message": "Match request Declined successfully"}, status=status.HTTP_200_OK)

