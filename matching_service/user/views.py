from django.contrib.auth import get_user_model
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated

from .serializers import UserProfileSerializer


class UserProfileView(RetrieveUpdateAPIView):
    """
       Reads and updates UserModel fields
       Accepts GET, PUT, PATCH methods.

       Default accepted fields: username, first_name, last_name, phone_number, age, gender
       Default display fields: pk, username, email, first_name, last_name, phone_number, gender
       Read-only fields: pk, email

       Returns UserModel fields.
       """
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated,]

    def get_object(self):
        return self.request.user

    def get_queryset(self):
        """
        Adding this method since it is sometimes called when using
        django-rest-swagger
        """
        return get_user_model().objects.none()
