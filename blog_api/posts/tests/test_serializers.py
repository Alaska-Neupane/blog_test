import pytest
from django.contrib.auth.models import User
from posts.models import Post, Tag, Comment, Profile
from posts.searilizers import PostSerializer, CommentSerializer, TagSerializer, ProfileSerializer
from rest_framework.test import APIRequestFactory

@pytest.mark.django_db
def test_post_serializer_create_assigns_author():
    factory = APIRequestFactory()
    user = User.objects.create_user(username='alaska', password='1234')
    request = factory.post('/api/posts/')
    request.user = user

    data = {'title': 'My Post', 'slug': 'my-post', 'content': 'Testing content', 'status': 'published'}
    serializer = PostSerializer(data=data, context={'request': request})
    assert serializer.is_valid(), serializer.errors
    post = serializer.save()
    assert post.author == user
    assert post.slug == 'my-post'

@pytest.mark.django_db
def test_comment_serializer_auto_author_and_approved():
    factory = APIRequestFactory()
    user = User.objects.create_user(username='alaska', password='1234')
    post = Post.objects.create(title='Test Post', slug='test', content='hello', author=user)
    request = factory.post('/api/comments/')
    request.user = user
    data = {'post': post.id, 'content': 'Nice article!'}
    serializer = CommentSerializer(data=data, context={'request': request})
    assert serializer.is_valid(), serializer.errors
    comment = serializer.save()
    assert comment.author == user
    assert comment.approved is True

@pytest.mark.django_db
def test_tag_serializer_basic():
    tag = Tag.objects.create(name='django', slug='django')
    serializer = TagSerializer(tag)
    assert serializer.data['name'] == 'django'

@pytest.mark.django_db
def test_profile_serializer_roundtrip():
    user = User.objects.create_user(username='alaska', password='1234', email='a@test.com')
    profile = Profile.objects.create(user=user, username='alaska', email='a@test.com', full_name='Alaska Dev')
    serializer = ProfileSerializer(profile)
    assert serializer.data['username'] == 'alaska'
