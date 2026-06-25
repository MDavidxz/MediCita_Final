from django.urls import path
from .views import login_view
from accounts import views

urlpatterns = [
    path('', login_view, name='login'),
    path('register/', views.register, name='register'),
    path('logout/', views.logout_view, name='logout'),
]