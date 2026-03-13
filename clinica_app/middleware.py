from django.shortcuts import redirect
from django.urls import reverse

class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # URLs que qualquer pessoa (mesmo deslogada) pode acessar
        exempt_urls = [
            reverse('home'),
            reverse('login'),
            reverse('doLogin'),
            '/admin/', # Adicione esta linha para liberar o painel do Django
        ]

        # Verifica se o usuário não está logado E se a URL atual não começa com os caminhos liberados
        if not request.user.is_authenticated:
            # Verifica se o caminho atual não está na lista de exceções
            if not any(request.path.startswith(url) for url in exempt_urls):
                return redirect('login')

        response = self.get_response(request)
        return response