from django.urls import path
from dj_rest_auth.registration.views import RegisterView
from dj_rest_auth.views import LoginView, LogoutView

from .views import UserProfileView, GetAMatch, MatchRequestListView, MatchRequestCreateView, \
    MatchRequestAcceptDeclineView, user_match_status

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('get-a-match/', GetAMatch.as_view(), name="get-a-match"),
    path('get-status/', user_match_status, name='user-status'),
    path('incoming-requests/', MatchRequestListView.as_view(), name='match-request-list'),
    path('send-request/<int:receiver_id>/', MatchRequestCreateView.as_view(), name='match-request-create'),
    path('api/match-requests/accept/<int:sender_id>/', MatchRequestAcceptDeclineView.as_view({'post': 'accept'}),
         name='match-request-accept'),
    path('api/match-requests/decline/<int:sender_id>/', MatchRequestAcceptDeclineView.as_view({'post': 'decline'}),
         name='match-request-decline'),
]
