from django.urls import path, include, re_path
from . import views
from .views import PostViewSet, TagViewSet, CommentViewSet
from rest_framework.routers import DefaultRouter
from django.conf import settings
from django.conf.urls.static import static

# HTML routes
urlpatterns = [
    path('', views.post_list, name='post_list'),
    path('posts/<slug:slug>/', views.post_detail, name='post_detail'),
    path('create/', views.create_post, name='create_post'),
    path('edit/<slug:slug>/', views.edit_post, name='edit_post'),
    path('delete/<slug:slug>/', views.delete_post, name='delete_post'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('register/', views.register_view, name='register'),
    path('profile/', views.profile_view, name='profile'),
    path('posts/<slug:slug>/comment/', views.add_comment, name='add_comment'),  
]

# API routes
router = DefaultRouter()
router.register(r'api/posts', PostViewSet, basename='post')
router.register(r'api/tags', TagViewSet, basename='tag')

urlpatterns += [
    path('', include(router.urls)),
    path('api/posts/<slug:post_slug>/comments/', 
         CommentViewSet.as_view({'get': 'list', 'post': 'create'}), 
         name='post-comments'),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)