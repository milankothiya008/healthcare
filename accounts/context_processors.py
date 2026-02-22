"""Template context processors - safe profile picture URL for navbar etc."""

def profile_picture_url(request):
    """Provide safe profile_picture_url for base template (avoids ValueError when no file)."""
    url = None
    if request.user.is_authenticated and getattr(request.user, 'profile_picture', None):
        try:
            if request.user.profile_picture:
                url = request.user.profile_picture.url
        except (ValueError, AttributeError):
            pass
    return {'profile_picture_url': url}
