from django.shortcuts import render, get_object_or_404, redirect
from rest_framework import viewsets, filters
from .models import Post, Tag, Comment
from .searilizers import PostSerializer, TagSerializer, CommentSerializer
from rest_framework.permissions import IsAuthenticatedOrReadOnly, IsAuthenticated
from .permissions import IsAuthorOrReadOnly
from django_filters.rest_framework import DjangoFilterBackend
from django.contrib.auth.models import User
from django.contrib.auth import login, logout, authenticate
from django.views.decorators.csrf import csrf_protect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect,render
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from rest_framework import generics, status, permissions
from .models import Profile 
from .searilizers import ProfileSerializer
from django.http import JsonResponse
from litellm import completion
from django.conf import settings
import json
import re
import ast
import logging
from django.utils import timezone
import os
# Home page with search
def post_list(request):
    query = request.GET.get("q")
    posts_list = Post.objects.filter(status="published").order_by("-published_at")
    if query:
        posts_list = posts_list.filter(title__icontains=query) | posts_list.filter(content__icontains=query) | posts_list.filter(tags__name__icontains=query)

    paginator = Paginator(posts_list, 5)
    page_number = request.GET.get("page")
    posts = paginator.get_page(page_number)
    context = {"posts": posts, "user": request.user}
    return render(request, "posts/post_list.html", context)


# Post detail with comments + comment form
def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug, status="published")
    comments = post.comments.filter(approved=True)
    post.click_count += 1
    post.save(update_fields=['click_count'])

    # Check if image exists on disk
    if post.image and not post.image.storage.exists(post.image.name):
        post.image = None

    if request.method == "POST" and request.user.is_authenticated:
        content = request.POST.get("content")
        if content.strip():
            Comment.objects.create(post=post, author=request.user, content=content)
            return redirect("post_detail", slug=post.slug)

    return render(request, "posts/post_detail.html", {"post": post, "comments": comments})


def post_comments(request, slug):
    post = get_object_or_404(Post, slug=slug, status="published")
    comments = post.comments.filter(approved=True).order_by('-created_at')
    return render(request, "posts/post_comments.html", {"post": post, "comments": comments})

# --- Authentication ---
@csrf_protect
def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password1 = request.POST.get("password1")
        password2 = request.POST.get("password2")
        if password1 != password2:
            return render(request, "registration/register.html", {"error": "Passwords do not match"})
        if User.objects.filter(username=username).exists():
            return render(request, "registration/register.html", {"error": "Username already exists"})
        user = User.objects.create_user(username=username, email=email, password=password1)
        login(request, user)
        return redirect("post_list")
    return render(request, "registration/register.html")


@csrf_protect
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("post_list")
        else:
            messages.error(request, "Wrong Credintals!! Please enter correct details.")
            return render(request, "registration/login.html", {"error": "Invalid credentials"})
    return render(request, "registration/login.html")


def logout_view(request):
    logout(request)
    return redirect("post_list")


@login_required
def profile_view(request):
    return render(request, "registration/profile.html", {"user": request.user})


@login_required
def create_post(request):
    if request.method == "POST":
        title = request.POST.get("title")
        slug = slugify(request.POST.get("slug", title))
        content = request.POST.get("content")
        status = request.POST.get("status")
        published_at = request.POST.get("published_at")
        image = request.FILES.get("image")  
        if Post.objects.filter(slug=slug).exists():
            return render(request, "posts/create_post.html", {"error": "Slug already exists"})

        post = Post.objects.create(
            author=request.user,
            title=title,
            slug=slug,
            content=content,
            status=status,
            published_at=published_at if published_at else None,
            image=image,
        )
        return redirect("post_detail", slug=post.slug)
    return render(request, "posts/create_post.html")

@login_required
def create_post_ai(request):
    if request.method == "POST":
        prompt = request.POST.get("ai_prompt", "").strip()
        if not prompt:
            return render(request, "posts/create_post_ai.html", {"error": "Please enter a prompt!"})

        try:
            # Call AI to generate blog content
            response = completion(
                model="gemini/gemini-flash-lite-latest",
                messages=[
                    {
                        "role": "user",
                        "content":  f"Generate a detailed blog post about: \"{prompt}\".\n\n"
                                     "Return your output ONLY as a valid JSON object, with these exact keys:\n"
                                     "- title (string)\n"
                                     "- content (string)\n"
                                     "- excerpt (string)\n\n"
                                    "Rules:\n"
                                     "1. Do not include any text before or after the JSON.\n"
                                    "2. Do not use markdown or code blocks.\n"
                                    "3. The JSON must be valid and directly parsable using json.loads()."
                    }
                ],
                api_key=settings.GEMINI_API_KEY,
                log_file="litellm_logs.txt"
            )

            ai_output = response['choices'][0]['message']['content']
            # parse and clean AI output into title/content/excerpt
            
            parsed = json.loads(ai_output)
            title = parsed.get('title') or 'Post'
            content = parsed.get('content')
            excerpt = (parsed.get('excerpt') or content[:150])[:150]

            # Create the post
            post = Post.objects.create(
                author=request.user,
                title=title,
                slug=slugify(title)[:50],
                content=content,
                excerpt=excerpt,
                status="published",
                published_at=timezone.now()
            )

            return redirect("post_detail", slug=post.slug)

        except Exception as e:
            return render(request, "posts/create_post_ai.html", {"error": str(e)})

    return render(request, "posts/create_post_ai.html")


@login_required
def edit_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if post.author != request.user:
        return redirect("post_detail", slug=slug)

    if request.method == "POST":
        post.title = request.POST.get("title")
        post.slug = slugify(request.POST.get("slug", post.title))
        post.content = request.POST.get("content")
        post.status = request.POST.get("status")
        post.published_at = request.POST.get("published_at") or None

        if "image" in request.FILES:  # only update if new image uploaded
            post.image = request.FILES["image"]

        post.save()
        return redirect("post_detail", slug=post.slug)

    return render(request, "posts/edit_post.html", {"post": post})
@login_required
def delete_post(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if post.author != request.user:
        return redirect("post_detail", slug=slug)
    if request.method == "POST":
        post.delete()
        return redirect("post_list")
    return redirect("edit_post", slug=slug)


# --- API ViewSets ---
class PostViewSet(viewsets.ModelViewSet):
    queryset = Post.objects.all()
    serializer_class = PostSerializer
    permission_classes = [IsAuthenticatedOrReadOnly, IsAuthorOrReadOnly]
    lookup_field = "slug"
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ["tags__slug", "status"]
    search_fields = ["title", "content", "tags__name"]
    ordering = ["-published_at"]

    def get_queryset(self):
        if self.action in ["list", "retrieve"]:
            return Post.objects.filter(status="published")
        return Post.objects.all()

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)

    def perform_update(self, serializer):
       if 'image' in self.request.FILES:
          serializer.save(author=self.request.user, image=self.request.FILES['image'])
       else:
           serializer.save(author=self.request.user)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.click_count += 1
        instance.save(update_fields=['click_count'])  
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


class TagViewSet(viewsets.ModelViewSet):
    queryset = Tag.objects.all()
    serializer_class = TagSerializer
    permission_classes = [IsAuthenticated]


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        # Support either the explicit 'post_slug' kwarg or nested router's 'post_pk'
        post_slug = self.kwargs.get('post_slug') or self.kwargs.get('post_pk') or self.request.query_params.get('post')
        if post_slug:
            return Comment.objects.filter(post__slug=post_slug, approved=True)
        return super().get_queryset()

    def perform_create(self, serializer):
        # Attach the post (by slug from URL or nested kwarg) and the requesting user as author
        post_slug = self.kwargs.get('post_slug') or self.kwargs.get('post_pk')
        if post_slug:
            post = get_object_or_404(Post, slug=post_slug)
            serializer.save(post=post, author=self.request.user, approved=True)
        else:
            # fallback: expect 'post' in validated data
            serializer.save(author=self.request.user)

def add_comment(request, slug):
    post = get_object_or_404(Post, slug=slug)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Comment.objects.create(post=post, author=request.user, content=content, approved=True)
    return redirect('post_detail', slug=slug)

    
class TestView(APIView):
    # explicitly setting throttles for this view
    throttle_classes = [UserRateThrottle, AnonRateThrottle]

    def get(self, request, *args, **kwargs):
        return Response({"message": "hello", "user": str(request.user)})


class ProfileUpdateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def _get_profile(self, user):
        profile, created = Profile.objects.get_or_create(
            user=user,
            defaults={
                "auth_id": str(user.pk),
                "username": getattr(user, "username", f"user_{user.pk}"),
                "email": getattr(user, "email", None),
                "full_name": user.get_full_name() if hasattr(user, "get_full_name") else "",
            },
        )
        return profile

    def get(self, request):
        profile = self._get_profile(request.user)
        serializer = ProfileSerializer(profile, context={"request": request})
        return Response(serializer.data)

    def put(self, request):
        profile = self._get_profile(request.user)
        serializer = ProfileSerializer(profile, data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request):
        profile = self._get_profile(request.user)
        serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

@login_required
def generate_blog(request):
    if request.method == "POST":
        prompt = request.POST.get("ai_prompt", "")
        return render(request, "posts/create_post.html", {"message": "Blog generated!"})
    return render(request, "posts/create_post.html")


class GenerateBlogAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        prompt = request.data.get("prompt")
        if not prompt:
            return Response({"error": "Prompt is required"}, status=400)

        try:
            response = completion(
                model="gemini/gemini-flash-lite-latest",
                messages=[{
                    "role": "user",
                    "content": f"Generate a detailed blog post about: {prompt}. "
                               f"Return JSON with keys: title, content, excerpt."
                }],
                api_key=settings.GEMINI_API_KEY,
                log_file="litellm_logs.txt"
            )
            ai_output = response['choices'][0]['message']['content']
            parsed = parse_and_clean_ai_output(ai_output)
            # Ensure we have sensible defaults when parsing failed
            title = parsed.get('title') or f"AI: {prompt}"
            content = parsed.get('content') or ai_output
            excerpt = parsed.get('excerpt') or (content[:150])

            post = Post.objects.create(
                author=request.user,
                title=title,
                slug=slugify(title)[:50],
                content=content,
                excerpt=excerpt,
                status="draft"
            )

            serializer = PostSerializer(post)
            return Response(serializer.data)

        except Exception as e:
            return Response({"error": str(e)}, status=500)
