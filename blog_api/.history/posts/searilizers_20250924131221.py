from rest_framework import serializers
from .models import Post, Tag, Comment
from django.contrib.auth.models import User

# Nested serializer for author
class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username')

# Tag serializer
class TagSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tag
        fields = ('id', 'name', 'slug')

# Comment serializer
class CommentSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ('id', 'post', 'author', 'content', 'created_at', 'approved')
        read_only_fields = ('author', 'approved', 'created_at')

    def create(self, validated_data):
        # Automatically assign the currently logged-in user as author
        validated_data['author'] = self.context['request'].user
        # Optionally, auto-approve comments (set approved=True)
        validated_data['approved'] = True
        return super().create(validated_data)

# Post serializer with image upload support
class PostSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)
    tags = TagSerializer(many=True, read_only=True)
    comments = CommentSerializer(many=True, read_only=True)
    image = serializers.ImageField(required=False, allow_null=True)  # support optional image

    class Meta:
        model = Post
        fields = (
            'id', 'author', 'title', 'slug', 'content', 'excerpt',
            'status', 'published_at', 'created_at', 'updated_at',
            'tags', 'comments', 'image'
        )
        read_only_fields = ('author', 'comments', 'created_at', 'updated_at','click_count')

    def create(self, validated_data):
        validated_data['author'] = self.context['request'].user
        return super().create(validated_data)

    def update(self, instance, validated_data):
        # Allow image to be updated
        image = validated_data.get('image', None)
        if image is not None:
            instance.image = image
        return super().update(instance, validated_data)
  
    def get_image(self, obj):
        if obj.image:
            request = self.context.get('request')
            return request.build_absolute_uri(obj.image.url)
        return None