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
from django.contrib.auth import login, authenticate, logout
from django.shortcuts import get_object_or_404, render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
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
    if request.method == "POST" and request.user.is_authenticated:
        content = request.POST.get("content")
        if content.strip():
            Comment.objects.create(post=post, author=request.user, content=content)
            return redirect("post_detail", slug=post.slug)

    return render(request, "posts/post_detail.html", {"post": post, "comments": comments})


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
