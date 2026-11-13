from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from decimal import Decimal
from .models import Insumo


def login_view(request):
    if request.user.is_authenticated:
        return redirect('cadastrar_insumo')

    error = None
    if request.method == 'POST':
        usuario_digitado = request.POST.get('username')
        senha_digitada = request.POST.get('password')
        user = authenticate(request, username=usuario_digitado, password=senha_digitada)

        if user is not None:
            login(request, user)
            return redirect('cadastrar_insumo')
        else:
            error = "Usuário ou senha inválidos."

    return render(request, 'login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home_view(request):
    # Por enquanto, redireciona a tela inicial direto para o cadastro de insumos
    return redirect('cadastrar_insumo')


@login_required
def cadastrar_insumo_view(request):
    sucesso = None

    if request.method == 'POST':
        nome = request.POST.get('nome_insumo')
        unidade = request.POST.get('unidade_de_medida')
        custo = Decimal(request.POST.get('custo').replace(',', '.'))
        qtd_unitaria = Decimal(request.POST.get('quantidade_unitaria').replace(',', '.'))
        qtd_estoque = Decimal(request.POST.get('quantidade_estoque', 0).replace(',', '.'))
        
        fornecedor = request.POST.get('fornecedor')
        telefone = request.POST.get('telefone')
        email = request.POST.get('email')

        # Cria e salva o insumo (o models.py calcula o preco_unitario e cria o histórico sozinho)
        Insumo.objects.create(
            nome_insumo=nome,
            unidade_de_medida=unidade,
            custo=custo,
            quantidade_unitaria=qtd_unitaria,
            quantidade_estoque=qtd_estoque,
            fornecedor=fornecedor,
            telefone=telefone,
            email=email,
            usuario=request.user  # Salva automaticamente como dono o usuário logado
        )

        sucesso = f"Insumo '{nome}' cadastrado!"

    return render(request, 'cadastrar_insumo.html', {'sucesso': sucesso})
