from rest_framework import serializers

from .models import CustomUser, MatchRequest


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


class MatchRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchRequest
        # fields = '__all__'
        exclude = ('sender','receiver','state','timestamp')

