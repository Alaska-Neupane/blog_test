from django.urls import path, include, re_path
from . import views
from .views import PostViewSet, TagViewSet, CommentViewSet
from rest_framework.routers import DefaultRouter
from rest_framework_nested.routers import NestedDefaultRouter
from django.conf import settings
from django.conf.urls.static import static
from .views import ProfileUpdateView
# HTML routes

urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('posts/<slug:slug>/', views.post_detail, name='post_detail'),
    path('posts/<slug:slug>/comments/', views.post_comments, name='post_comments'),
    path('create/', views.create_post, name='create_post'),
    path('edit/<slug:slug>/', views.edit_post, name='edit_post'),
    path('delete/<slug:slug>/', views.delete_post, name='delete_post'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('api/me/', ProfileUpdateView.as_view(), name='profile-update'), 
    path('profile/', views.profile_view, name='profile'),
    path('posts/<slug:slug>/comment/', views.add_comment, name='add_comment'),  
    path('test/', views.TestView.as_view(), name='test'),  # Test view with throttling
    
]

# API routes
router = DefaultRouter()
router.register(r'api/posts', PostViewSet, basename='post')
router.register(r'api/tags', TagViewSet, basename='tag')

# Nested router so comments are available under a specific post URL
posts_router = NestedDefaultRouter(router, r'api/posts', lookup='post')
posts_router.register(r'comments', CommentViewSet, basename='post-comments')

urlpatterns += [
    path('', include(router.urls)),
    path('', include(posts_router.urls)),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)


