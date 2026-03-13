from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import CustomUser, Dentista, Paciente, Procedimento, Consulta
from django.utils import timezone
from django.shortcuts import render, redirect
from django.db.models import Q
from datetime import date
from django.contrib.auth.decorators import login_required
import uuid

def home(request):
    return render(request, 'home.html')

def loginUser(request):
    return render(request, 'login_page.html')

def doLogin(request):
    if request.method != "POST":
        return redirect('login')
    
    email = request.POST.get("email")
    password = request.POST.get("password")
    user = authenticate(request, username=email, password=password)
    
    if user is not None:
        login(request, user)
        user_type = str(user.user_type)
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
@login_required
def gerente_home(request):
    if str(request.user.user_type) != "1":
        messages.error(request, "Acesso restrito a gerentes.")
        return redirect('home')
    return render(request, 'gerente_template/home.html')

@login_required
def dentista_home(request):
    if str(request.user.user_type) != "2":
        messages.error(request, "Acesso restrito a dentistas.")
        return redirect('home')
        
    try:
        dentista_obj = Dentista.objects.get(admin=request.user) # Use o objeto direto
        hoje = date.today()
        consultas = Consulta.objects.filter(dentista_id=dentista_obj).order_by('data_consulta')
        
        # Filtro de busca
        query = request.GET.get('q')
        if query:
            consultas = consultas.filter(
                Q(paciente_id__admin__first_name__icontains=query) | 
                Q(paciente_id__admin__last_name__icontains=query)
            )

        consultas_hoje = Consulta.objects.filter(dentista_id=dentista_obj, data_consulta__date=hoje)
        
        context = {
            "dentista": dentista_obj,
            "consultas": consultas,
            "total_pacientes": consultas_hoje.values('paciente_id').distinct().count(),
            "total_consultas": consultas_hoje.count(),
            "consultas_pendentes": consultas_hoje.filter(status=False).count(),
            "hoje": hoje,
        }
        return render(request, 'dentista_template/home.html', context)
        
    except Dentista.DoesNotExist:
        messages.error(request, "Perfil de dentista não encontrado.")
        return redirect('logout_user')

@login_required
def paciente_home(request):
    if str(request.user.user_type) != "3":
        return redirect('home')
    return render(request, 'paciente_template/home.html')

def add_dentista(request):
    return render(request, "gerente_template/add_dentista_template.html")

def add_dentista_save(request):
    if request.method != "POST":
        return redirect('add_dentista')
    
    nome_completo = request.POST.get('nome_completo')
    email = request.POST.get('email')
    password = request.POST.get('password')
    cro = request.POST.get('cro')
    cpf = request.POST.get('cpf')

    # Validações de duplicidade
    if CustomUser.objects.filter(username=email).exists():
        messages.error(request, "E-mail já cadastrado!")
        return redirect('add_dentista')
    
    if Dentista.objects.filter(cro=cro).exists():
        messages.error(request, "Este CRO já está registrado!")
        return redirect('add_dentista')

    try:
        user = CustomUser.objects.create_user(
            username=email, password=password, email=email,
            first_name=nome_completo, last_name="", user_type='2'
        )
        # O signal já criou o dentista, agora apenas preenchemos
        dentista = user.dentista
        dentista.address = request.POST.get('address')
        dentista.especialidade = request.POST.get('especialidade')
        dentista.cro = cro
        dentista.cpf = cpf
        dentista.telefone = request.POST.get('telefone')
        
        data_nasc = request.POST.get('data_nascimento')
        if data_nasc: dentista.data_nascimento = data_nasc
        
        dentista.save()
        messages.success(request, f"Dentista {nome_completo} cadastrado!")
        return redirect('manage_dentista')
    except Exception as e:
        messages.error(request, f"Erro: {e}")
        return redirect('add_dentista')

def manage_dentista(request):
    dentistas = Dentista.objects.all() # Busca todos os dentistas
    return render(request, "gerente_template/manage_dentista_template.html", {"dentistas": dentistas})

def delete_dentista(request, dentista_id):
    try:
        # Buscamos o dentista pelo ID do CustomUser (admin_id)
        user = CustomUser.objects.get(id=dentista_id)
        nome = user.first_name
        user.delete() # Isso deleta o Dentista automaticamente via CASCADE
        messages.success(request, f"Dentista {nome} removido com sucesso.")
    except Exception as e:
        messages.error(request, f"Erro ao excluir: {e}")
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
    
    try:
        # Usamos get() para buscar o usuário pelo ID
        user = CustomUser.objects.get(id=dentista_id)
        
        # Salvando o nome completo no first_name
        user.first_name = request.POST.get('nome_completo')
        user.last_name = "" 
        user.email = request.POST.get('email') # Não esqueça do email se ele mudar!
        user.save()

        # Acessando o objeto dentista relacionado
        dentista = user.dentista
        dentista.especialidade = request.POST.get('especialidade')
        dentista.cro = request.POST.get('cro')
        dentista.address = request.POST.get('address')
        dentista.cpf = request.POST.get('cpf')
        dentista.telefone = request.POST.get('telefone')
        dentista.data_nascimento = request.POST.get('data_nascimento')
        
        dentista.save()
        messages.success(request, f"Dados do(a) Dr(a). {user.first_name} atualizados com sucesso!")

    except CustomUser.DoesNotExist:
        messages.error(request, "Usuário não encontrado.")
    except Exception as e:
        messages.error(request, f"Erro ao atualizar: {e}")
    
    return redirect('manage_dentista')

# Listar Pacientes
def manage_paciente(request):
    pacientes = Paciente.objects.all()
    return render(request, "gerente_template/manage_paciente_template.html", {"pacientes": pacientes})

# Página de Cadastro
def add_paciente(request):
    return render(request, "gerente_template/add_paciente_template.html")

def add_paciente_save(request):
    if request.method != "POST":
        return redirect('add_paciente')

    data = request.POST
    nome_completo = data.get('nome_completo')
    email = data.get('email')
    cpf = data.get('cpf')

    if CustomUser.objects.filter(username=email).exists():
        messages.error(request, "Este e-mail já está sendo usado.")
        return render(request, 'gerente_template/add_paciente_template.html', {'dados': data})
    
    # CORREÇÃO AQUI: Adicionado 'gerente_template/'
    if cpf and Paciente.objects.filter(cpf=cpf).exists():
        messages.error(request, "Este CPF já está cadastrado.")
        return render(request, 'gerente_template/add_paciente_template.html', {'dados': data})

    try:
        user = CustomUser.objects.create_user(
            username=email, password=str(uuid.uuid4()), email=email,
            first_name=nome_completo, user_type='3'
        )
        
        paciente = user.paciente
        paciente.genero = data.get('genero')
        paciente.cpf = cpf
        paciente.telefone = data.get('telefone')
        paciente.address = data.get('address')
        paciente.historico_medico = data.get('historico_medico')
        
        data_nasc = data.get('data_nascimento')
        if data_nasc: paciente.data_nascimento = data_nasc
        
        paciente.save()
        messages.success(request, f"Paciente {nome_completo} cadastrado!")
        return redirect('manage_paciente')

    except Exception as e:
        messages.error(request, f"Erro crítico: {e}")
        # CORREÇÃO AQUI: Adicionado 'gerente_template/'
        return render(request, 'gerente_template/add_paciente_template.html', {'dados': data})
    
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
    
    try:
        # Busca o usuário pelo ID vindo do input hidden
        user = CustomUser.objects.get(id=paciente_id)
        
        # Salvando o Nome Completo no campo first_name e limpando o last_name
        user.first_name = request.POST.get('nome_completo')
        user.last_name = "" 
        user.email = request.POST.get('email')
        user.save()

        # Acessando o model Paciente (extensão do User)
        paciente = user.paciente
        paciente.address = request.POST.get('address')
        paciente.genero = request.POST.get('genero')
        paciente.historico_medico = request.POST.get('historico_medico')
        
        # --- NOVOS CAMPOS ATUALIZADOS ---
        paciente.cpf = request.POST.get('cpf')
        paciente.telefone = request.POST.get('telefone')
        paciente.data_nascimento = request.POST.get('data_nascimento')
        # -------------------------------
        
        paciente.save()

        messages.success(request, f"Cadastro de {user.first_name} atualizado com sucesso!")
        
    except CustomUser.DoesNotExist:
        messages.error(request, "Paciente não encontrado no sistema.")
    except Exception as e:
        messages.error(request, f"Erro ao atualizar paciente: {e}")
        
    return redirect('manage_paciente')

# Deletar Paciente
def delete_paciente(request, paciente_id):
    try:
        # Buscamos o paciente pelo ID do CustomUser (admin_id)
        user = CustomUser.objects.get(id=paciente_id)
        nome = user.first_name
        user.delete() # Isso deleta o Paciente automaticamente via CASCADE
        messages.success(request, f"Paciente {nome} removido com sucesso.")
    except Exception as e:
        messages.error(request, f"Erro ao excluir: {e}")
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

def dentista_manage_paciente(request):
    query = request.GET.get('q')
    pacientes = Paciente.objects.all()

    if query:
        pacientes = pacientes.filter(
            Q(admin__first_name__icontains=query) | 
            Q(admin__last_name__icontains=query)
        )

    return render(request, "dentista_template/manage_paciente.html", {"pacientes": pacientes, "query": query})

def dentista_view_paciente(request, paciente_id):
    paciente = Paciente.objects.get(id=paciente_id)
    # Pegamos todas as consultas desse paciente com este dentista
    historico_consultas = Consulta.objects.filter(paciente_id=paciente).order_by('-data_consulta')
    
    context = {
        "paciente": paciente,
        "consultas": historico_consultas
    }
    return render(request, "dentista_template/view_paciente.html", context)