import uuid,os
from django.db import models
from django.conf import settings
from django.utils.text import slugify
from PIL import Image
from django.utils import timezone
class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    auth_id = models.CharField(max_length=255, unique=True)
    full_name = models.CharField(max_length=255, blank=True, null=True)
    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True, null=True)
    avatar_url = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.username or self.user.username


class Tag(models.Model):
    name = models.CharField(max_length=50, unique=True)
    slug = models.SlugField(unique=True)

    def __str__(self):
        return self.name


class Post(models.Model):
    STATUS_CHOICES = (
        ("draft", "Draft"),
        ("published", "Published")
    )

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True, blank=True)
    content = models.TextField()
    excerpt = models.TextField(blank=True)
    image = models.ImageField(upload_to="posts/images/post_detail_img", blank=True, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    published_at = models.DateTimeField(null=True, blank=True, auto_now_add=True,)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    tags = models.ManyToManyField(Tag, through='PostTag', blank=True)
    click_count = models.PositiveIntegerField(default=0) 
    def save(self, *args, **kwargs):
        if self.status == "published" and not self.published_at:
              self.published_at = timezone.now()
        if not self.slug:
            self.slug = slugify(self.title)
        super().save(*args, **kwargs)
        if self.image:

            img = Image.open(self.image.path)
            img = img.convert("RGB")
            img.thumbnail((400, 400))

            base, ext = os.path.splitext(os.path.basename(self.image.name))
            thumb_filename = f"{base}_thumb.jpg"
            thumb_path = os.path.join(settings.MEDIA_ROOT, "posts/images/post_list_img", thumb_filename)

            os.makedirs(os.path.dirname(thumb_path), exist_ok=True)

            img.save(thumb_path, "JPEG", quality=70, optimize=True)
            self._thumbnail_name = f"posts/images/post_list_img/{thumb_filename}"

    @property
    def thumbnail_url(self):
        if hasattr(self, "_thumbnail_name"):
            return os.path.join(settings.MEDIA_URL, self._thumbnail_name)
        if self.image:
            base, _ = os.path.splitext(os.path.basename(self.image.name))
            thumb_filename = f"{base}_thumb.jpg"
            return os.path.join(settings.MEDIA_URL, "posts/images/post_list_img", thumb_filename)
        return None

    def __str__(self):
        return self.title

class PostTag(models.Model):
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    tag = models.ForeignKey(Tag, on_delete=models.CASCADE)


class Comment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    approved = models.BooleanField(default=True)

    def __str__(self):
        return f"Comment by {self.author} on {self.post}"
