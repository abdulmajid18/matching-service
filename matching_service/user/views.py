from django.db.models import Q
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView, get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import CustomUser, Match
from .serializers import UserProfileSerializer, AgeRangeSerializer
from .utils.matching_algo import request_a_match, matching_algorithm


class UserProfileView(RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated, ]

    def get_object(self):
        return self.request.user


class MatchWithUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None, *args, **kwargs):
        # get authenticated user from request
        authenticated_user = request.user
        # get targeted user from CustomUser
        targeted_user = get_object_or_404(CustomUser, pk=user_id)
        # verify if targeted user is available for matching
        match_exists = Match.objects.filter(Q(user1=targeted_user) | Q(user2=targeted_user), state='Unmatch').exists()
        if match_exists:
            # send a request to be matched
            response = request_a_match(authenticated_user, targeted_user)
            return Response({'status': response})
        return Response({'detail': "user can't be matched, check suggested potential matches"})


class SuggestMatchesView(APIView):
    permission_classes = [IsAuthenticated]

    def user_unmatched(self, user):
        # check if user is unmatched so we can suggest available users
        return Match.objects.filter(Q(user1=user) | Q(user2=user), state='Unmatch').exists()

    def post(self, request, *args, **kwargs):
        # Get authenticated user
        requested_user = request.user

        # Check if the user already has a match
        user_has_match = Match.objects.filter(Q(user1=requested_user) | Q(user2=requested_user)).exists()

        if user_has_match:
            if not self.user_unmatched(requested_user):
                return Response({"detail": "You are currently matched"}, status=status.HTTP_400_BAD_REQUEST)

        # Deserialize request data
        serializer = AgeRangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        # Get age range from serializer
        min_age = serializer.validated_data.get("min_age")
        max_age = serializer.validated_data.get("max_age")

        # Perform matching algorithm
        queryset = matching_algorithm(min_age, max_age, requested_user)
        serializer = UserProfileSerializer(queryset, many=True)

        # If the user doesn't have a match, initialize a match
        if not user_has_match:
            initialized_match = Match.objects.create(user1=requested_user)
            initialized_match.save()

        return Response({'possible_matches': serializer.data}, status=status.HTTP_201_CREATED)
