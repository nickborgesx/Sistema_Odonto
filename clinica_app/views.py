from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from .models import CustomUser, Dentista, Paciente, Procedimento, Consulta, Recepcionista
from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.utils import timezone
import re

# --- AUXILIARES E VALIDAÇÕES ---

def _redirect_user_home(request):
    """Redireciona o usuário logado conforme seu nível de acesso."""
    user_type = str(getattr(request.user, "user_type", ""))
    redirect_map = {
        "1": "gerente_home",
        "2": "dentista_home",
        "3": "paciente_home",
        "4": "recepcionista_home",
    }
    url = redirect_map.get(user_type)
    if url:
        return redirect(url)
    messages.error(request, "Tipo de usuário inválido.")
    logout(request)
    return redirect("home")

def limpar_valor(valor):
    if not valor: return ""
    return re.sub(r"\D", "", str(valor))

def cpf_eh_valido(cpf):
    cpf = limpar_valor(cpf)
    if len(cpf) != 11 or cpf == cpf[0] * 11:
        return False
    def calc_dv(base, tamanho):
        total = sum(int(base[i]) * (tamanho + 1 - i) for i in range(tamanho))
        dv = (total * 10) % 11
        return 0 if dv == 10 else dv
    return calc_dv(cpf, 9) == int(cpf[9]) and calc_dv(cpf, 10) == int(cpf[10])

def normalizar_telefone(telefone):
    tel = limpar_valor(telefone)
    if tel.startswith("55") and len(tel) in (12, 13): tel = tel[2:]
    return tel

def validar_cpf_global(cpf_limpo, exclude_id=None, model_type=None):
    """Garante que o CPF não esteja em uso em nenhuma das tabelas de perfil."""
    q_dentista = Dentista.objects.filter(cpf=cpf_limpo)
    q_paciente = Paciente.objects.filter(cpf=cpf_limpo)
    q_recep = Recepcionista.objects.filter(cpf=cpf_limpo)

    if model_type == 'dentista' and exclude_id: q_dentista = q_dentista.exclude(id=exclude_id)
    if model_type == 'paciente' and exclude_id: q_paciente = q_paciente.exclude(id=exclude_id)
    if model_type == 'recepcionista' and exclude_id: q_recep = q_recep.exclude(id=exclude_id)

    return q_dentista.exists() or q_paciente.exists() or q_recep.exists()

# --- AUTENTICAÇÃO ---

def home(request):
    if request.user.is_authenticated:
        return _redirect_user_home(request)
    return render(request, "home.html")

def doLogin(request):
    if request.method != "POST": return redirect('home')
    email = (request.POST.get("email") or "").strip()
    password = request.POST.get("password") or ""
    user = authenticate(request, username=email, password=password)
    
    if user is None and email:
        try:
            candidate = CustomUser.objects.get(email=email)
            user = authenticate(request, username=candidate.username, password=password)
        except CustomUser.DoesNotExist: pass

    if user is not None:
        login(request, user)
        return _redirect_user_home(request)
    
    messages.error(request, "E-mail ou senha inválidos.")
    return redirect('home')

def logout_user(request):
    logout(request)
    return redirect('home')

# --- DASHBOARDS ---

@login_required
def gerente_home(request):
    if str(request.user.user_type) != "1": return redirect('home')
    return render(request, 'gerente_template/home.html')

@login_required
def recepcionista_home(request):
    if str(request.user.user_type) != "4": return redirect('home')
    return render(request, "recepcionista_template/home.html")

@login_required
def paciente_home(request):
    if str(request.user.user_type) != "3": return redirect('home')
    return render(request, 'paciente_template/home.html')

@login_required
def dentista_home(request):
    if str(request.user.user_type) != "2": return redirect('home')
    try:
        dentista_obj = Dentista.objects.get(admin=request.user)
        hoje = timezone.localdate()
        consultas_base = Consulta.objects.filter(dentista_id=dentista_obj).select_related("paciente_id__admin", "procedimento_id")
        
        query = (request.GET.get("q") or "").strip()
        consultas_busca = None
        if query:
            filtro = Q(paciente_id__admin__first_name__icontains=query) | Q(paciente_id__admin__last_name__icontains=query)
            cpf_limpo = limpar_valor(query)
            if cpf_limpo: filtro |= Q(paciente_id__cpf__icontains=cpf_limpo)
            consultas_busca = consultas_base.filter(filtro).order_by("-data_consulta")

        context = {
            "dentista": dentista_obj,
            "agenda_hoje": consultas_base.filter(data_consulta__date=hoje, status=False),
            "consultas_realizadas_hoje": consultas_base.filter(data_consulta__date=hoje, status=True).count(),
            "consultas_pendentes_hoje": consultas_base.filter(data_consulta__date=hoje, status=False).count(),
            "hoje": hoje, "q": query, "consultas_busca": consultas_busca,
        }
        return render(request, 'dentista_template/home.html', context)
    except Dentista.DoesNotExist:
        logout(request); return redirect('home')

# --- GERENCIAMENTO DE DENTISTAS (GERENTE) ---

@login_required
def manage_dentista(request):
    if str(request.user.user_type) != "1": return redirect('home')
    return render(request, "gerente_template/manage_dentista_template.html", {"dentistas": Dentista.objects.all()})

@login_required
def add_dentista(request):
    if str(request.user.user_type) != "1": return redirect('home')
    return render(request, "gerente_template/add_dentista_template.html")

@login_required
def add_dentista_save(request):
    if request.method != "POST" or str(request.user.user_type) != "1": return redirect('manage_dentista')
    nome, email, cpf_limpo = request.POST.get('nome_completo'), request.POST.get('email'), limpar_valor(request.POST.get('cpf'))
    
    if not cpf_eh_valido(cpf_limpo) or validar_cpf_global(cpf_limpo):
        messages.error(request, "CPF inválido ou já cadastrado."); return redirect('add_dentista')
    
    try:
        user = CustomUser.objects.create_user(username=email, email=email, password=request.POST.get('password'), first_name=nome, user_type='2')
        d = user.dentista
        d.cpf, d.telefone, d.cro = cpf_limpo, normalizar_telefone(request.POST.get('telefone')), request.POST.get('cro')
        d.especialidade, d.address, d.data_nascimento = request.POST.get('especialidade'), request.POST.get('address'), request.POST.get('data_nascimento')
        d.save()
        messages.success(request, f"Dr(a). {nome} cadastrado(a)!")
    except Exception as e: messages.error(request, f"Erro: {e}")
    return redirect('manage_dentista')

@login_required
def edit_dentista(request, dentista_id):
    if str(request.user.user_type) != "1": return redirect('home')
    u = get_object_or_404(CustomUser, id=dentista_id)
    return render(request, "gerente_template/edit_dentista_template.html", {"dentista": u.dentista, "usuario_edit": u})

@login_required
def edit_dentista_save(request):
    if request.method != "POST" or str(request.user.user_type) != "1": return redirect('manage_dentista')
    try:
        user = CustomUser.objects.get(id=request.POST.get('dentista_id'))
        d, cpf_limpo = user.dentista, limpar_valor(request.POST.get('cpf'))
        if not cpf_eh_valido(cpf_limpo) or validar_cpf_global(cpf_limpo, exclude_id=d.id, model_type='dentista'):
            messages.error(request, "CPF inválido ou em uso."); return redirect('manage_dentista')
        
        user.first_name, user.email = request.POST.get('nome_completo'), request.POST.get('email'); user.save()
        d.cpf, d.telefone, d.cro = cpf_limpo, normalizar_telefone(request.POST.get('telefone')), request.POST.get('cro')
        d.especialidade, d.address = request.POST.get('especialidade'), request.POST.get('address')
        d.data_nascimento = request.POST.get('data_nascimento') or d.data_nascimento; d.save()
        messages.success(request, "Cadastro atualizado!")
    except Exception as e: messages.error(request, f"Erro: {e}")
    return redirect('manage_dentista')

@login_required
def delete_dentista(request, dentista_id):
    if str(request.user.user_type) != "1": return redirect('home')
    get_object_or_404(CustomUser, id=dentista_id).delete()
    messages.success(request, "Registro removido."); return redirect('manage_dentista')

# --- GERENCIAMENTO DE PACIENTES ---

@login_required
def manage_paciente(request):
    if str(request.user.user_type) not in ["1", "4"]: return redirect('home')
    q = (request.GET.get("q") or "").strip()
    pacientes = Paciente.objects.all()
    if q:
        q_cpf = limpar_valor(q)
        filtro = Q(admin__first_name__icontains=q) | Q(admin__last_name__icontains=q)
        if q_cpf:
            filtro = filtro | Q(cpf__icontains=q_cpf)
        pacientes = pacientes.filter(filtro)
    return render(request, "gerente_template/manage_paciente_template.html", {"pacientes": pacientes, "query": q})

@login_required
def add_paciente(request):
    if str(request.user.user_type) not in ["1", "4"]: return redirect('home')
    return render(request, "gerente_template/add_paciente_template.html")

@login_required
def add_paciente_save(request):
    if request.method != "POST" or str(request.user.user_type) not in ["1", "4"]: return redirect('manage_paciente')
    cpf_limpo = limpar_valor(request.POST.get('cpf'))
    if not cpf_eh_valido(cpf_limpo) or validar_cpf_global(cpf_limpo):
        messages.error(request, "CPF inválido."); return redirect('manage_paciente')
    try:
        email = request.POST.get('email')
        user = CustomUser.objects.create_user(username=email, email=email, password=request.POST.get("password") or "odonto123", first_name=request.POST.get('nome_completo'), user_type='3')
        p = user.paciente
        p.cpf, p.telefone, p.genero = cpf_limpo, normalizar_telefone(request.POST.get('telefone')), request.POST.get("genero")
        p.address, p.historico_medico = request.POST.get('address'), request.POST.get("historico_medico")
        p.data_nascimento = request.POST.get("data_nascimento") or None; p.save()
        messages.success(request, "Paciente cadastrado!")
    except Exception as e: messages.error(request, f"Erro: {e}")
    return redirect('manage_paciente')

@login_required
def edit_paciente(request, paciente_id):
    if str(request.user.user_type) not in ["1", "4"]: return redirect('home')
    u = get_object_or_404(CustomUser, id=paciente_id)
    # Evita sobrescrever `user` do Django (request.user) no template/base.html
    return render(request, "gerente_template/edit_paciente_template.html", {"paciente": u.paciente, "usuario_edit": u})

@login_required
def edit_paciente_save(request):
    if request.method != "POST" or str(request.user.user_type) not in ["1", "4"]: return redirect('manage_paciente')
    try:
        user = CustomUser.objects.get(id=request.POST.get('paciente_id'))
        p, cpf_limpo = user.paciente, limpar_valor(request.POST.get('cpf'))
        if not cpf_eh_valido(cpf_limpo) or validar_cpf_global(cpf_limpo, exclude_id=p.id, model_type='paciente'):
            messages.error(request, "CPF inválido."); return redirect('manage_paciente')
        user.first_name, user.email = request.POST.get('nome_completo'), request.POST.get('email'); user.save()
        p.cpf, p.telefone, p.genero = cpf_limpo, normalizar_telefone(request.POST.get('telefone')), request.POST.get("genero")
        p.address, p.historico_medico = request.POST.get('address'), request.POST.get("historico_medico")
        p.data_nascimento = request.POST.get("data_nascimento") or p.data_nascimento; p.save()
        messages.success(request, "Paciente atualizado!")
    except Exception as e: messages.error(request, f"Erro: {e}")
    return redirect('manage_paciente')

@login_required
def delete_paciente(request, paciente_id):
    if str(request.user.user_type) not in ["1", "4"]: return redirect('home')
    get_object_or_404(CustomUser, id=paciente_id).delete()
    messages.success(request, "Paciente removido."); return redirect('manage_paciente')

# --- GERENCIAMENTO DE CONSULTAS ---

@login_required
def manage_consulta(request):
    if str(request.user.user_type) not in ["1", "4"]: return redirect('home')
    return render(request, "gerente_template/manage_consulta_template.html", {"consultas": Consulta.objects.all().order_by('-data_consulta')})

# --- GERENCIAMENTO DE CONSULTAS (Atualizado para incluir Médicos/Dentistas) ---

@login_required
def add_consulta(request):
    # Adicionado "2" na lista de permissões
    if str(request.user.user_type) not in ["1", "2", "4"]: 
        return redirect('home')
    
    dentistas = Dentista.objects.all()
    dentistas_options = []
    for d in dentistas:
        u = d.admin
        full_name = f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip()
        label = full_name or (u.email or u.username or f"Dentista #{d.id}")
        dentistas_options.append({"id": d.id, "label": label})

    context = {
        "pacientes": Paciente.objects.all(),
        "dentistas": dentistas,
        "dentistas_options": dentistas_options,
        "procedimentos": Procedimento.objects.all()
    }
    return render(request, "gerente_template/add_consulta_template.html", context)

@login_required
def add_consulta_save(request):
    if request.method != "POST": 
        return redirect('manage_consulta')
    
    # Adicionado "2" na validação de permissão do POST
    if str(request.user.user_type) not in ["1", "2", "4"]:
        return redirect('home')

    try:
        p_id = request.POST.get('paciente')
        if not p_id:
            # Lógica para busca por CPF se o select estiver vazio
            match = re.search(r"CPF:\s*([0-9.\-]+)", request.POST.get("paciente_nome", ""))
            paciente_obj = Paciente.objects.get(cpf=limpar_valor(match.group(1))) if match else None
        else: 
            paciente_obj = Paciente.objects.get(id=p_id)
        
        if not paciente_obj: 
            messages.error(request, "Selecione um paciente válido.")
            return redirect("add_consulta")
        
        Consulta.objects.create(
            paciente_id=paciente_obj, 
            dentista_id=Dentista.objects.get(id=request.POST.get('dentista')), 
            procedimento_id=Procedimento.objects.get(id=request.POST.get('procedimento')), 
            data_consulta=request.POST.get('data_consulta'), 
            status=False
        )
        messages.success(request, "Consulta agendada com sucesso!")
    except Exception as e: 
        messages.error(request, f"Erro ao agendar: {e}")
    
    # Redireciona para a home do usuário (cada um para sua respectiva dashboard)
    return _redirect_user_home(request)

@login_required
def edit_consulta(request, consulta_id):
    if str(request.user.user_type) not in ["1", "4"]: return redirect('home')
    dentistas = Dentista.objects.all()
    dentistas_options = []
    for d in dentistas:
        u = d.admin
        full_name = f"{(u.first_name or '').strip()} {(u.last_name or '').strip()}".strip()
        label = full_name or (u.email or u.username or f"Dentista #{d.id}")
        dentistas_options.append({"id": d.id, "label": label})

    context = {
        "consulta": get_object_or_404(Consulta, id=consulta_id),
        "pacientes": Paciente.objects.all(),
        "dentistas": dentistas,
        "dentistas_options": dentistas_options,
        "procedimentos": Procedimento.objects.all(),
    }
    return render(request, "gerente_template/edit_consulta_template.html", context)

@login_required
def edit_consulta_save(request):
    if request.method != "POST": return redirect('manage_consulta')
    try:
        c = Consulta.objects.get(id=request.POST.get('consulta_id'))
        c.paciente_id = Paciente.objects.get(id=request.POST.get('paciente'))
        c.dentista_id = Dentista.objects.get(id=request.POST.get('dentista'))
        c.procedimento_id = Procedimento.objects.get(id=request.POST.get('procedimento'))
        c.data_consulta = request.POST.get('data_consulta')
        c.status = request.POST.get('status') == '1'; c.save()
        messages.success(request, "Consulta atualizada!")
    except Exception as e: messages.error(request, f"Erro: {e}")
    return redirect('manage_consulta')

@login_required
def delete_consulta(request, consulta_id):
    if str(request.user.user_type) not in ["1", "4"]: return redirect('home')
    get_object_or_404(Consulta, id=consulta_id).delete()
    messages.success(request, "Agendamento removido."); return redirect('manage_consulta')

@login_required
def dentista_finalizar_consulta(request, consulta_id):
    if str(request.user.user_type) != "2": return redirect("home")
    c = get_object_or_404(Consulta, id=consulta_id, dentista_id__admin=request.user)
    c.status = True; c.save(update_fields=["status"])
    messages.success(request, "Consulta finalizada!"); return redirect("dentista_home")

# --- PROCEDIMENTOS ---

@login_required
def manage_procedimento(request):
    if str(request.user.user_type) != "1": return redirect('home')
    return render(request, "gerente_template/manage_procedimento_template.html", {"procedimentos": Procedimento.objects.all()})

@login_required
def add_procedimento_save(request):
    if request.method == "POST" and str(request.user.user_type) == "1":
        Procedimento.objects.create(nome=request.POST.get('nome'), valor=request.POST.get('valor').replace(',', '.'))
        messages.success(request, "Procedimento adicionado!")
    return redirect('manage_procedimento')

@login_required
def edit_procedimento_save(request):
    if request.method != "POST" or str(request.user.user_type) != "1": return redirect('manage_procedimento')
    try:
        p = Procedimento.objects.get(id=request.POST.get('procedimento_id'))
        p.nome = request.POST.get('nome')
        p.valor = request.POST.get('valor').replace(',', '.')
        p.save()
        messages.success(request, "Procedimento atualizado!")
    except Exception as e: messages.error(request, f"Erro: {e}")
    return redirect('manage_procedimento')

@login_required
def delete_procedimento(request, procedimento_id):
    if str(request.user.user_type) == "1":
        get_object_or_404(Procedimento, id=procedimento_id).delete(); messages.success(request, "Removido!")
    return redirect('manage_procedimento')

# --- RECEPCIONISTAS ---

@login_required
def manage_recepcionista(request):
    if str(request.user.user_type) != "1": return redirect('home')
    return render(request, "gerente_template/manage_recepcionista_template.html", {"recepcionistas": Recepcionista.objects.all()})

@login_required
def add_recepcionista(request):
    if str(request.user.user_type) != "1": return redirect('home')
    return render(request, "gerente_template/add_recepcionista_template.html")

@login_required
def add_recepcionista_save(request):
    if request.method != "POST" or str(request.user.user_type) != "1": return redirect('manage_recepcionista')
    cpf_limpo = limpar_valor(request.POST.get('cpf'))
    if not cpf_eh_valido(cpf_limpo) or validar_cpf_global(cpf_limpo):
        messages.error(request, "CPF inválido."); return redirect('add_recepcionista')
    try:
        email = request.POST.get('email')
        user = CustomUser.objects.create_user(username=email, email=email, password=request.POST.get('password'), first_name=request.POST.get('nome_completo'), user_type='4')
        r = user.recepcionista
        r.cpf, r.telefone, r.endereco = cpf_limpo, normalizar_telefone(request.POST.get('telefone')), request.POST.get('endereco')
        r.data_nascimento = request.POST.get('data_nasc'); r.save()
        messages.success(request, "Recepcionista cadastrado!")
    except Exception as e: messages.error(request, f"Erro: {e}")
    return redirect('manage_recepcionista')

@login_required
def edit_recepcionista(request, recepcionista_id):
    if str(request.user.user_type) != "1": return redirect('home')
    u = get_object_or_404(CustomUser, id=recepcionista_id)
    return render(request, "gerente_template/edit_recepcionista_template.html", {"recepcionista": u.recepcionista, "usuario_editado": u})

@login_required
def edit_recepcionista_save(request):
    if request.method != "POST" or str(request.user.user_type) != "1": return redirect('manage_recepcionista')
    try:
        user = CustomUser.objects.get(id=request.POST.get('recepcionista_id'))
        r, cpf_limpo = user.recepcionista, limpar_valor(request.POST.get('cpf'))
        if not cpf_eh_valido(cpf_limpo) or validar_cpf_global(cpf_limpo, exclude_id=r.id, model_type='recepcionista'):
            messages.error(request, "CPF inválido."); return redirect('manage_recepcionista')
        user.first_name, user.email = request.POST.get('nome_completo'), request.POST.get('email'); user.save()
        r.cpf, r.telefone, r.endereco = cpf_limpo, normalizar_telefone(request.POST.get('telefone')), request.POST.get('endereco')
        r.data_nascimento = request.POST.get('data_nasc') or r.data_nascimento; r.save()
        messages.success(request, "Dados atualizados!")
    except Exception as e: messages.error(request, f"Erro: {e}")
    return redirect('manage_recepcionista')

@login_required
def delete_recepcionista(request, recepcionista_id):
    if str(request.user.user_type) != "1": return redirect('home')
    get_object_or_404(CustomUser, id=recepcionista_id).delete()
    messages.success(request, "Removido com sucesso."); return redirect('manage_recepcionista')

# --- ÁREA DENTISTA (ESPECÍFICO) ---

@login_required
def dentista_manage_paciente(request):
    if str(request.user.user_type) != "2": return redirect('home')
    q = (request.GET.get('q') or "").strip()
    pacientes = Paciente.objects.all()
    if q:
        q_cpf = limpar_valor(q)
        filtro = Q(admin__first_name__icontains=q) | Q(admin__last_name__icontains=q)
        if q_cpf:
            filtro = filtro | Q(cpf__icontains=q_cpf)
        pacientes = pacientes.filter(filtro)
    return render(request, "dentista_template/manage_paciente.html", {"pacientes": pacientes, "query": q})

@login_required
def dentista_view_paciente(request, paciente_id):
    if str(request.user.user_type) != "2": return redirect('home')
    p = get_object_or_404(Paciente, id=paciente_id)
    return render(request, "dentista_template/view_paciente.html", {"paciente": p, "consultas": Consulta.objects.filter(paciente_id=p).order_by('-data_consulta')})
