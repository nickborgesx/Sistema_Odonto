
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import CustomUser, Dentista, Paciente, Procedimento, Consulta
from django.utils import timezone
from django.shortcuts import render, redirect
from django.http import HttpResponse, HttpResponseRedirect


def home(request):
    return render(request, 'home.html')

def loginUser(request):
    return render(request, 'login_page.html')

def doLogin(request):
    if request.method != "POST":
        # Em vez de HttpResponse, vamos apenas mandar de volta para o login
        return redirect('login')
    
    email = request.POST.get("email")
    password = request.POST.get("password")
    
    user = authenticate(request, username=email, password=password)
    
    if user is not None:
        login(request, user)
        # Redirecionamento por tipo de usuário
        user_type = str(user.user_type) # Convertendo para string para garantir a comparação
        
        if user_type == "1":
            return redirect('gerente_home')
        elif user_type == "2":
            return redirect('dentista_home')
        elif user_type == "3":
            return redirect('paciente_home')
        else:
            return redirect('home')
    else:
        messages.error(request, "E-mail ou senha inválidos.")
        return redirect('login')

def logout_user(request):
    logout(request)
    return redirect('home')

# Placeholders para as futuras Dashboards (vamos criá-las depois)
def gerente_home(request):
    return render(request, 'gerente_template/home.html')

def dentista_home(request):
    # 1. Pegamos o objeto Dentista que está vinculado ao Usuário logado
    try:
        dentista_obj = Dentista.objects.get(admin=request.user.id)
        
        # 2. Buscamos as consultas USANDO O OBJETO DENTISTA (e não o ID do user)
        consultas = Consulta.objects.filter(dentista_id=dentista_obj).order_by('data_consulta')
        
        context = {
            "consultas": consultas,
            "total_pacientes": consultas.values('paciente_id').distinct().count(),
            "total_consultas": consultas.count(),
            "consultas_pendentes": consultas.filter(status=False).count(),
        }
    except Dentista.DoesNotExist:
        # Caso o usuário logado não seja um dentista cadastrado
        return redirect('logout_user')

    return render(request, 'dentista_template/home.html', context)

def paciente_home(request):
    return render(request, 'paciente_template/home.html')

from .models import Dentista, CustomUser # Certifique-se de que estão importados

def add_dentista(request):
    return render(request, "gerente_template/add_dentista_template.html")

def add_dentista_save(request):
    if request.method != "POST":
        return redirect('add_dentista')
    
    first_name = request.POST.get('first_name')
    last_name = request.POST.get('last_name')
    email = request.POST.get('email')
    password = request.POST.get('password')
    especialidade = request.POST.get('especialidade')
    cro = request.POST.get('cro')
    address = request.POST.get('address')

    try:
        # 1. Cria o usuário base
        user = CustomUser.objects.create_user(
            username=email, 
            password=password, 
            email=email, 
            first_name=first_name, 
            last_name=last_name, 
            user_type=2 # 2 é o tipo Dentista
        )
        # 2. O Signal que criamos no models.py já criará o objeto Dentista,
        # então vamos apenas atualizar os campos extras:
        dentista = user.dentista
        dentista.especialidade = especialidade
        dentista.cro = cro
        dentista.address = address
        dentista.save()

        messages.success(request, "Dentista cadastrado com sucesso!")
        return redirect('add_dentista')
    except Exception as e:
        messages.error(request, f"Erro ao cadastrar dentista: {e}")
        return redirect('add_dentista')

def manage_dentista(request):
    dentistas = Dentista.objects.all() # Busca todos os dentistas
    return render(request, "gerente_template/manage_dentista_template.html", {"dentistas": dentistas})

def delete_dentista(request, dentista_id):
    dentista = Dentista.objects.get(admin=dentista_id)
    user = CustomUser.objects.get(id=dentista_id)
    try:
        user.delete() # Deletando o CustomUser, o Django deleta o Dentista automaticamente (Cascade)
        messages.success(request, "Dentista removido com sucesso!")
    except:
        messages.error(request, "Erro ao remover dentista.")
    return redirect('manage_dentista')

def edit_dentista(request, dentista_id):
    # Busca o usuário e os dados do dentista para preencher o formulário
    user = CustomUser.objects.get(id=dentista_id)
    dentista = user.dentista
    return render(request, "gerente_template/edit_dentista_template.html", {"dentista": dentista, "user": user})

def edit_dentista_save(request):
    if request.method != "POST":
        return redirect('manage_dentista')
    
    dentista_id = request.POST.get('dentista_id')
    first_name = request.POST.get('first_name')
    last_name = request.POST.get('last_name')
    email = request.POST.get('email')
    especialidade = request.POST.get('especialidade')
    cro = request.POST.get('cro')
    address = request.POST.get('address')

    try:
        # 1. Atualiza o usuário base
        user = CustomUser.objects.get(id=dentista_id)
        user.first_name = first_name
        user.last_name = last_name
        user.email = email
        user.username = email
        user.save()

        # 2. Atualiza os dados específicos do dentista
        dentista = user.dentista
        dentista.especialidade = especialidade
        dentista.cro = cro
        dentista.address = address
        dentista.save()

        messages.success(request, "Dados do dentista atualizados com sucesso!")
        return redirect('manage_dentista')
    except Exception as e:
        messages.error(request, f"Erro ao atualizar: {e}")
        return redirect('manage_dentista')

from .models import Paciente # Certifique-se de importar o modelo

# Listar Pacientes
def manage_paciente(request):
    pacientes = Paciente.objects.all()
    return render(request, "gerente_template/manage_paciente_template.html", {"pacientes": pacientes})

# Página de Cadastro
def add_paciente(request):
    return render(request, "gerente_template/add_paciente_template.html")

# Salvar Cadastro
def add_paciente_save(request):
    if request.method != "POST":
        return redirect('add_paciente')
    
    first_name = request.POST.get('first_name')
    last_name = request.POST.get('last_name')
    email = request.POST.get('email')
    password = request.POST.get('password')
    address = request.POST.get('address')
    genero = request.POST.get('genero')
    historico = request.POST.get('historico_medico')

    try:
        user = CustomUser.objects.create_user(username=email, password=password, email=email, first_name=first_name, last_name=last_name, user_type=3)
        paciente = user.paciente
        paciente.address = address
        paciente.genero = genero
        paciente.historico_medico = historico
        paciente.save()
        messages.success(request, "Paciente cadastrado com sucesso!")
        return redirect('manage_paciente')
    except Exception as e:
        messages.error(request, f"Erro ao cadastrar: {e}")
        return redirect('add_paciente')

# Editar Paciente
def edit_paciente(request, paciente_id):
    user = CustomUser.objects.get(id=paciente_id)
    paciente = user.paciente
    return render(request, "gerente_template/edit_paciente_template.html", {"paciente": paciente, "user": user})

# Salvar Edição
def edit_paciente_save(request):
    if request.method != "POST":
        return redirect('manage_paciente')
    
    paciente_id = request.POST.get('paciente_id')
    user = CustomUser.objects.get(id=paciente_id)
    user.first_name = request.POST.get('first_name')
    user.last_name = request.POST.get('last_name')
    user.email = request.POST.get('email')
    user.save()

    paciente = user.paciente
    paciente.address = request.POST.get('address')
    paciente.genero = request.POST.get('genero')
    paciente.historico_medico = request.POST.get('historico_medico')
    paciente.save()

    messages.success(request, "Dados do paciente atualizados!")
    return redirect('manage_paciente')

# Deletar Paciente
def delete_paciente(request, paciente_id):
    user = CustomUser.objects.get(id=paciente_id)
    user.delete()
    messages.success(request, "Paciente removido.")
    return redirect('manage_paciente')

def dentista_home(request):
    # Obtemos o objeto Dentista ligado ao usuário logado
    dentista_obj = Dentista.objects.get(admin=request.user.id)
    
    # Contagens para o Dashboard
    total_pacientes = Consulta.objects.filter(dentista_id=dentista_obj).values('paciente_id').distinct().count()
    total_consultas = Consulta.objects.filter(dentista_id=dentista_obj).count()
    consultas_pendentes = Consulta.objects.filter(dentista_id=dentista_obj, status=False).count()

    context = {
        "total_pacientes": total_pacientes,
        "total_consultas": total_consultas,
        "consultas_pendentes": consultas_pendentes,
    }
    return render(request, 'dentista_template/home.html', context)

# Listar e Mostrar Formulário de Cadastro (Tudo na mesma página para agilizar)
def manage_procedimento(request):
    procedimentos = Procedimento.objects.all()
    return render(request, "gerente_template/manage_procedimento_template.html", {"procedimentos": procedimentos})

def add_procedimento_save(request):
    if request.method != "POST":
        return redirect('manage_procedimento')
    
    nome = request.POST.get('nome')
    valor = request.POST.get('valor').replace(',', '.') # Garante que aceite vírgula como ponto decimal

    try:
        procedimento = Procedimento(nome=nome, valor=valor)
        procedimento.save()
        messages.success(request, "Procedimento adicionado com sucesso!")
    except Exception as e:
        messages.error(request, f"Erro ao adicionar: {e}")
    
    return redirect('manage_procedimento')

def edit_procedimento_save(request):
    if request.method != "POST":
        return redirect('manage_procedimento')
    
    id = request.POST.get('procedimento_id')
    nome = request.POST.get('nome')
    valor = request.POST.get('valor').replace(',', '.')

    try:
        procedimento = Procedimento.objects.get(id=id)
        procedimento.nome = nome
        procedimento.valor = valor
        procedimento.save()
        messages.success(request, "Procedimento atualizado!")
    except Exception as e:
        messages.error(request, f"Erro ao atualizar: {e}")
    
    return redirect('manage_procedimento')

def delete_procedimento(request, procedimento_id):
    try:
        procedimento = Procedimento.objects.get(id=procedimento_id)
        procedimento.delete()
        messages.success(request, "Procedimento removido.")
    except:
        messages.error(request, "Erro ao remover.")
    return redirect('manage_procedimento')

def add_consulta(request):
    # Buscamos todos os dados necessários para as opções do select
    pacientes = Paciente.objects.all()
    dentistas = Dentista.objects.all()
    procedimentos = Procedimento.objects.all()
    
    context = {
        "pacientes": pacientes,
        "dentistas": dentistas,
        "procedimentos": procedimentos
    }
    return render(request, "gerente_template/add_consulta_template.html", context)

def add_consulta_save(request):
    if request.method != "POST":
        return redirect('add_consulta')
    
    paciente_id = request.POST.get('paciente')
    dentista_id = request.POST.get('dentista')
    procedimento_id = request.POST.get('procedimento')
    data_consulta = request.POST.get('data_consulta')

    try:
        # Buscamos as instâncias dos objetos pelos IDs enviados pelo form
        paciente_obj = Paciente.objects.get(id=paciente_id)
        dentista_obj = Dentista.objects.get(id=dentista_id)
        procedimento_obj = Procedimento.objects.get(id=procedimento_id)

        # Criamos a consulta
        consulta = Consulta(
            paciente_id=paciente_obj,
            dentista_id=dentista_obj,
            procedimento_id=procedimento_obj,
            data_consulta=data_consulta,
            status=False # Inicia como pendente
        )
        consulta.save()
        messages.success(request, "Consulta agendada com sucesso!")
        return redirect('gerente_home') # Ou uma página de listagem de consultas
    except Exception as e:
        messages.error(request, f"Erro ao agendar: {e}")
        return redirect('add_consulta')

def edit_consulta(request, consulta_id):
    consulta = Consulta.objects.get(id=consulta_id)
    pacientes = Paciente.objects.all()
    dentistas = Dentista.objects.all()
    procedimentos = Procedimento.objects.all()
    
    context = {
        "consulta": consulta,
        "pacientes": pacientes,
        "dentistas": dentistas,
        "procedimentos": procedimentos
    }
    return render(request, "gerente_template/edit_consulta_template.html", context)

def edit_consulta_save(request):
    if request.method != "POST":
        return redirect('gerente_home')
    
    consulta_id = request.POST.get('consulta_id')
    
    try:
        consulta = Consulta.objects.get(id=consulta_id)
        
        # Atualizando com os novos IDs vindos do form
        consulta.paciente_id = Paciente.objects.get(id=request.POST.get('paciente'))
        consulta.dentista_id = Dentista.objects.get(id=request.POST.get('dentista'))
        consulta.procedimento_id = Procedimento.objects.get(id=request.POST.get('procedimento'))
        consulta.data_consulta = request.POST.get('data_consulta')
        
        # Opcional: permitir que o gerente mude o status
        status = request.POST.get('status')
        consulta.status = True if status == '1' else False
        
        consulta.save()
        messages.success(request, "Consulta atualizada com sucesso!")
    except Exception as e:
        messages.error(request, f"Erro ao atualizar consulta: {e}")
        
    return redirect('gerente_home') # Ou para uma lista de todas as consultas

def manage_consulta(request):
    consultas = Consulta.objects.all().order_by('-data_consulta')
    return render(request, "gerente_template/manage_consulta_template.html", {"consultas": consultas})

def delete_consulta(request, consulta_id):
    try:
        consulta = Consulta.objects.get(id=consulta_id)
        consulta.delete()
        messages.success(request, "Agendamento removido com sucesso!")
    except:
        messages.error(request, "Erro ao remover agendamento.")
    return redirect('manage_consulta')