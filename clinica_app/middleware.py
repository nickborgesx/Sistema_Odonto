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

        # Verifica se o usuário não está logado E se a URL atual não começa com os caminhos liberados
        if not request.user.is_authenticated:
            # Evita o bug de `startswith('/')` liberar tudo: paths exatos vs. prefixos.
            if request.path not in exempt_exact_paths and not request.path.startswith(exempt_prefixes):
                return redirect('home')

        response = self.get_response(request)
        return response
