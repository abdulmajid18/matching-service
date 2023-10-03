from rest_framework import serializers

from .models import CustomUser, MatchUsers


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


class AgeRangeSerializer(serializers.Serializer):
    min_age = serializers.IntegerField(min_value=18)
    max_age = serializers.IntegerField(max_value=100, min_value=18)


class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'gender', 'phone_number', 'age']







