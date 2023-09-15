from rest_framework import serializers

from . models import CustomUser


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = (
            'pk',
            'email',
            'phone_number',
            'gender',
            'first_name',
            'last_name',
            'username',
            'age'
        )
        read_only_fields = ('pk', 'email',)


