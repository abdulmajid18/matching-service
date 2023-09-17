from django.urls import path
from dj_rest_auth.registration.views import RegisterView
from dj_rest_auth.views import LoginView, LogoutView


from .views import UserProfileView, SuggestMatchesView, MatchWithUserView

urlpatterns = [
    path('auth/register/', RegisterView.as_view(), name='register'),
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('profile/', UserProfileView.as_view(), name='profile'),
    path('suggest-matches/', SuggestMatchesView.as_view(), name="suggest-matchers"),
    path('<int:user_id>/request-to-match/', MatchWithUserView.as_view(), name='request'),
]
