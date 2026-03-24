from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs que qualquer pessoa (mesmo deslogada) pode acessar
        exempt_exact_paths = {
            reverse('home'),
            reverse('doLogin'),
        }
        exempt_prefixes = (
            '/admin/',  # libera admin (inclui /admin/login/)
        )


        if not request.user.is_authenticated:
            if request.path not in exempt_exact_paths and not request.path.startswith(exempt_prefixes):
                return redirect('home')

        response = self.get_response(request)
        return response
