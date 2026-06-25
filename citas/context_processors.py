from django.templatetags.static import static

def logo_processor(request):
    return {
        'logo_url': static('citas/img/logo.png'),
        'default_avatar_url': static('citas/img/default_avatar.png'),
    }