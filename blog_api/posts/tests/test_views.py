import pytest
from django.urls import reverse
from rest_framework.test import APIClient
from django.contrib.auth.models import User
from posts.models import Post, Comment, Tag, Profile

@pytest.fixture
def client():
    return APIClient()

@pytest.mark.django_db
def test_get_post_list(client):
    user = User.objects.create_user(username='alaska', password='alaska')
    Post.objects.create(title='Hello', slug='hello', content='World', author=user, status='published')
    url = reverse('post-list')
    response = client.get(url)
    assert response.status_code == 200
    assert response.data[0]['title'] == 'Hello'

@pytest.mark.django_db
def test_create_post_authenticated(client):
    user = User.objects.create_user(username='alaska', password='alaska')
    client.force_authenticate(user=user)
    url = reverse('post-list')
    data = {'title': 'My New Post', 'slug': 'new-post', 'content': 'Hi', 'status': 'published'}
    response = client.post(url, data, format='json')
    assert response.status_code == 201
    post = Post.objects.get(slug='new-post')
    assert post.author == user

@pytest.mark.django_db
def test_retrieve_post_increments_click_count(client):
    user = User.objects.create_user(username='alaska', password='1234')
    post = Post.objects.create(title='Click', slug='click', content='count', author=user, status='published')
    url = reverse('post-detail', args=['click'])
    old_clicks = post.click_count
    client.get(url)
    post.refresh_from_db()
    assert post.click_count == old_clicks + 1

@pytest.mark.django_db
def test_update_post_with_image(client, tmp_path):
    user = User.objects.create_user(username='alaska', password='1234')
    post = Post.objects.create(title='Old', slug='old', content='content', author=user, status='published')
    client.force_authenticate(user=user)
    url = reverse('post-detail', args=['old'])
    image_file = tmp_path / "test.jpg"
    image_file.write_text("fake image data")
    with open(image_file, "rb") as img:
        response = client.patch(url, {'title': 'Updated', 'image': img}, format='multipart')
    assert response.status_code in (200, 202)
    post.refresh_from_db()
    assert post.title == 'Updated'

@pytest.mark.django_db
def test_comment_create_auto_attach_post(client):
    user = User.objects.create_user(username='alaska', password='1234')
    post = Post.objects.create(title='Commented', slug='commented', content='x', author=user, status='published')
    client.force_authenticate(user=user)
    url = reverse('comment-list')
    data = {'post': post.id, 'content': 'Nice post!'}
    response = client.post(url, data, format='json')
    assert response.status_code == 201
    comment = Comment.objects.first()
    assert comment.post == post
    assert comment.author == user

@pytest.mark.django_db
def test_profile_get_and_patch(client):
    user = User.objects.create_user(username='alaska', password='1234', email='old@test.com')
    client.force_authenticate(user=user)
    url = reverse('profile-update')  
    response = client.get(url)
    assert response.status_code == 200
    data = {'full_name': 'Updated Name'}
    patch_res = client.patch(url, data, format='json')
    assert patch_res.status_code == 200
    profile = Profile.objects.get(user=user)
    assert profile.full_name == 'Updated Name'
