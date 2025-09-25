import requests
import jwt
from jwt import PyJWKClient
from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import authentication, exceptions

User = get_user_model()

class SupabaseJWTAuthentication(authentication.BaseAuthentication):
    """Authenticate requests using Supabase JWT (Bearer token)."""
    
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None
            
        try:
            scheme, token = auth_header.split()
        except ValueError:
            return None
            
        if scheme.lower() != 'bearer':
            return None

        # Use the existing Supabase URL from your settings
        jwks_url = f"{settings.SUPABASE_URL}/auth/v1/.well-known/jwks.json"
        
        try:
            jwk_client = PyJWKClient(jwks_url)
            signing_key = jwk_client.get_signing_key_from_jwt(token)
            
            # Enhanced token decoding with better error handling
            payload = jwt.decode(
                token, 
                signing_key.key, 
                algorithms=["RS256"], 
                options={"verify_aud": False}
            )
            
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed('Token has expired')
        except jwt.InvalidTokenError as e:
            raise exceptions.AuthenticationFailed(f'Invalid token: {str(e)}')
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Authentication failed: {str(e)}')

        supabase_user_id = payload.get('sub')
        if not supabase_user_id:
            raise exceptions.AuthenticationFailed('Token missing sub claim')

        # Use the email as username if available, otherwise use the supabase ID
        email = payload.get('email', '')
        username = email if email else supabase_user_id
        
        # Get or create user - enhanced to handle edge cases
        try:
            user, created = User.objects.get_or_create(
                username=username, 
                defaults={'email': email}
            )
            
            # Update email if it changed in Supabase
            if user.email != email and email:
                user.email = email
                user.save()
                
        except Exception as e:
            raise exceptions.AuthenticationFailed(f'Could not create user: {str(e)}')
        
        # Create or update profile - with error handling
        try:
            from .models import Profile
            profile, profile_created = Profile.objects.get_or_create(
                user=user, 
                defaults={
                    'auth_id': supabase_user_id,
                    'username': username,
                    'email': email  
                }
            )
            
            # Update profile if it already existed
            if not profile_created:
                profile.auth_id = supabase_user_id
                if hasattr(profile, 'email') and email:
                    profile.email = email
                profile.save()
                
        except Exception as e:
            # Don't fail authentication if profile creation fails
            print(f"Profile creation error: {str(e)}")
            # Continue with user authentication anyway
        
        return (user, token)

    def authenticate_header(self, request):
        """Return value for WWW-Authenticate header."""
        return 'Bearer realm="api"'