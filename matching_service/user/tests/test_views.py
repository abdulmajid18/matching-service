import json
import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from ..models import CustomUser, DeclinedMatch




class TestGetAMatchView:

    @pytest.fixture(scope="function")
    def client(self):
        return APIClient()

    @pytest.fixture(scope="function")
    def create_matching_users(self):
        user1 = CustomUser.objects.create_user(username="user1", password="password1")
        user2 = CustomUser.objects.create_user(username="user2", password="password2")
        user3 = CustomUser.objects.create_user(username="user3", password="password3")

        return user1, user2, user3

    @pytest.fixture(scope="function")
    def update_matching_users(self, create_matching_users):
        user1, user2, user3 = create_matching_users
        user1.first_name = "User1"
        user1.last_name = "USER"
        user1.gender = "M"
        user1.age = 20
        user1.phone_number = "555-555-5555"
        user1.save()

        user2.first_name = "User2"
        user2.last_name = "USER2"
        user2.gender = "M"
        user2.age = 25
        user2.phone_number = "555-555-5556"
        user2.save()

        user3.first_name = "User3"
        user3.last_name = "USER3"
        user3.gender = "M"
        user3.age = 26
        user3.phone_number = "555-555-5556"
        user3.save()

        return user1, user2, user3

    @pytest.fixture(scope="function")
    def check_user_status(self, client):
        def _check_status(user, expected_status):
            url = reverse('user-status')
            client.force_authenticate(user=user)
            response = client.get(url)
            response_data = response.data
            match_status = response_data["status"]
            assert match_status == expected_status

        return _check_status


    @pytest.fixture(scope="function")
    def check_request_status(self, client):
        def _check_request_status(user, expected_status):
            url = reverse('user-request-status')
            client.force_authenticate(user=user)
            response = client.get(url)
            response_data = response.data
            match_status = response_data["status"]
            assert match_status == expected_status

        return _check_request_status
    @pytest.mark.django_db
    def test_accept_state_transition(self, update_matching_users, client, check_user_status, check_request_status):
        user1, user2, user3 = update_matching_users
        # user1 get a match
        user1_data = {
            'min_age': 18,
            'max_age': 30,
        }

        url = reverse('get-a-match')
        client.force_authenticate(user=user1)
        response = client.post(url, user1_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        response_data = json.loads(response.content)
        assert 'possible_matches' in response_data

        # user2 get a match
        user2_data = {
            'min_age': 18,
            'max_age': 30,
        }
        client.force_authenticate(user=user2)
        url = reverse('get-a-match')
        user2_response = client.post(url, user2_data, format='json')
        assert user2_response.status_code == status.HTTP_201_CREATED
        user2_response_data = json.loads(user2_response.content)
        assert 'possible_matches' in user2_response_data

        # Check the status of user1 and user2
        check_user_status(user1, 'Unmatched')
        check_user_status(user2, 'Unmatched')

        # Send a match request from user2 to user1
        client.force_authenticate(user=user2)
        url = reverse('match-request-create', kwargs={'receiver_id': user1.id})
        response = client.post(url, format='json')
        assert response.data['state'] == 'Pending'

        # Check the status of user1 and user2
        check_user_status(user1, 'Pending')
        check_user_status(user2, 'Pending')

        # check if user3 can be suggested user1 an user2
        user3_data = {
            'min_age': 18,
            'max_age': 30,
        }
        url = reverse('get-a-match')
        user3_response = client.post(url, user3_data, format='json')
        assert user3_response.status_code == status.HTTP_201_CREATED
        user3_response_data = json.loads(user3_response.content)
        possible_matches = user3_response_data['possible_matches']
        assert len(possible_matches) == 0

        # check user1 incoming request,  should have a request from  user2
        client.force_authenticate(user=user1)
        url = reverse('match-request-list')
        response = client.get(url, format='json')
        username = response.data[0]['username']
        assert username == 'user2'

        # Accept the match request
        client.force_authenticate(user=user1)
        url = reverse('match-request-accept', kwargs={'sender_id': user2.id})
        response = client.post(url, format='json')
        assert response.data['message'] == 'Match request Accepted successfully'

        # checks the status of a sent request
        check_request_status(user2, 'Accepted')

        # # Check the status of user1 and user2
        check_user_status(user1, 'Matched')
        check_user_status(user2, 'Matched')

        # user3 makes a match request
        """ Since all users are current matched possible matches should be empty"""
        url = reverse('get-a-match')
        client.force_authenticate(user=user3)
        user3_data = {
            'min_age': 18,
            'max_age': 30,
        }
        user3_response = client.post(url, user3_data, format='json')
        assert user3_response.status_code == status.HTTP_201_CREATED
        user3_response_data = json.loads(user3_response.content)
        possible_matches = user3_response_data['possible_matches']
        assert len(possible_matches) == 0

        # user2 get a match should return a match
        user2_data = {
            'min_age': 18,
            'max_age': 30,
        }
        client.force_authenticate(user=user2)
        url = reverse('get-a-match')
        user2_response = client.post(url, user2_data, format='json')
        assert user2_response.status_code == status.HTTP_201_CREATED
        user2_response_data = json.loads(user2_response.content)
        assert user2_response_data['status'] == 'Matched'

        # user1 get a match should return a match
        user1_data = {
            'min_age': 18,
            'max_age': 30,
        }
        client.force_authenticate(user=user1)
        url = reverse('get-a-match')
        user1_response = client.post(url, user1_data, format='json')
        assert user1_response.status_code == status.HTTP_201_CREATED
        user1_response_data = json.loads(user1_response.content)
        assert user1_response_data['status'] == 'Matched'


    @pytest.mark.django_db
    def test_accept_state_transition(self, update_matching_users, client, check_user_status, check_request_status):
        user1, user2, user3 = update_matching_users
        # user1 get a match
        user1_data = {
            'min_age': 18,
            'max_age': 30,
        }

        url = reverse('get-a-match')
        client.force_authenticate(user=user1)
        response = client.post(url, user1_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        response_data = json.loads(response.content)
        assert 'possible_matches' in response_data

        # user2 get a match
        client.force_authenticate(user=user2)
        user2_data = {
            'min_age': 18,
            'max_age': 30,
        }
        url = reverse('get-a-match')
        user2_response = client.post(url, user2_data, format='json')
        assert user2_response.status_code == status.HTTP_201_CREATED
        user2_response_data = json.loads(user2_response.content)
        assert 'possible_matches' in user2_response_data

        # Check the status of user1 and user2
        check_user_status(user1, 'Unmatched')
        check_user_status(user2, 'Unmatched')

        # Send a match request from user2 to user1
        client.force_authenticate(user=user2)
        url = reverse('match-request-create', kwargs={'receiver_id': user1.id})
        response = client.post(url, format='json')
        assert response.data['state'] == 'Pending'

        # Check the status of user1 and user2
        check_user_status(user1, 'Pending')
        check_user_status(user2, 'Pending')

        # Decline the match request
        client.force_authenticate(user=user1)
        url = reverse('match-request-decline', kwargs={'sender_id': user2.id})
        response = client.post(url, format='json')
        assert response.data['message'] == 'Match request Declined successfully'

        # checks the status of a sent request
        check_request_status(user2, 'Declined')

        # Check the status of user1 and user2
        check_user_status(user1, 'Unmatched')
        check_user_status(user2, 'Unmatched')

        # Check if user2 is in user1 blocked requests
        user1_declined_requests: DeclinedMatch = DeclinedMatch.objects.filter(sender=user2).first()
        assert user1_declined_requests.receiver == user1

        # check if user1 is in user2's pool
        """ When user2 requests for match no user should be in the pool, since user2 is blocked by the only available
        user"""
        url = reverse('get-a-match')
        client.force_authenticate(user=user2)
        response = client.post(url, user2_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        response_data = json.loads(response.content)
        possible_matches = response_data['possible_matches']
        assert len(possible_matches) == 0


        # check if user2 is in user1's pool
        """ When user1 requests for match user2 shouldn't be in the pool"""
        url = reverse('get-a-match')
        client.force_authenticate(user=user1)
        response = client.post(url, user1_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        response_data = json.loads(response.content)
        possible_matches = response_data['possible_matches']
        assert len(possible_matches) == 0

        # check if user2 is in user1's pool
        """ When user1 requests for match user2 shouldn't be in the pool"""
        url = reverse('get-a-match')
        client.force_authenticate(user=user2)
        response = client.post(url, user2_data, format='json')
        assert response.status_code == status.HTTP_201_CREATED
        response_data = json.loads(response.content)
        possible_matches = response_data['possible_matches']
        assert len(possible_matches) == 0

        # user3 get a match
        """ When user3 requests for match all other users should be available ie user1 and user2"""
        client.force_authenticate(user=user3)
        user3_data = {
            'min_age': 18,
            'max_age': 30,
        }
        url = reverse('get-a-match')
        user3_response = client.post(url, user3_data, format='json')
        assert user3_response.status_code == status.HTTP_201_CREATED
        user3_response_data = json.loads(user3_response.content)
        possible_matches = user3_response_data['possible_matches']
        assert len(possible_matches) == 2

