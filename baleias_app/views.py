from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from .models import (
    Insumo, EstoquePrincipal, MovimentacaoEstoquePrincipal,
    PerfilFuncionario, SetorEstoque, ContagemDiariaSetor
)


def login_view(request):
    if request.user.is_authenticated:
        return redirect('estoque_principal' if request.user.is_superuser else 'contagem_mobile')

    error = None
    if request.method == 'POST':
        user = authenticate(request, username=request.POST.get('username'), password=request.POST.get('password'))
        if user is not None:
            login(request, user)
            return redirect('estoque_principal' if user.is_superuser else 'contagem_mobile')
        error = "Usuário ou senha inválidos."

    return render(request, 'login.html', {'error': error})


def logout_view(request):
    logout(request)
    return redirect('login')


@login_required
def home_view(request):
    return redirect('estoque_principal' if request.user.is_superuser else 'contagem_mobile')


@login_required
def cadastrar_insumo_view(request):
    if not request.user.is_superuser:
        return redirect('contagem_mobile')

    sucesso = None
    if request.method == 'POST':
        novo_insumo = Insumo.objects.create(
            nome_insumo=request.POST.get('nome_insumo'),
            unidade_de_medida=request.POST.get('unidade_de_medida'),
            custo=Decimal(request.POST.get('custo').replace(',', '.')),
            quantidade_unitaria=Decimal(request.POST.get('quantidade_unitaria').replace(',', '.')),
            fornecedor=request.POST.get('fornecedor'),
            telefone=request.POST.get('telefone'),
            email=request.POST.get('email'),
            usuario=request.user
        )
        EstoquePrincipal.objects.create(insumo=novo_insumo, quantidade_atual=0, gestor=request.user)
        sucesso = f"Insumo '{novo_insumo.nome_insumo}' cadastrado no catálogo!"

    return render(request, 'cadastrar_insumo.html', {'sucesso': sucesso})


@login_required
def estoque_principal_view(request):
    if not request.user.is_superuser:
        return redirect('contagem_mobile')

    mensagem = None
    busca = request.GET.get('busca', '').strip()

    if request.method == 'POST':
        acao = request.POST.get('acao')
        insumo_id = request.POST.get('insumo_id')
        qtd = Decimal(request.POST.get('quantidade', '0').replace(',', '.'))
        
        est_principal, _ = EstoquePrincipal.objects.get_or_create(
            insumo_id=insumo_id, defaults={'gestor': request.user}
        )

        if acao == 'adicionar_entrada':
            est_principal.quantidade_atual += qtd
            est_principal.save()
            MovimentacaoEstoquePrincipal.objects.create(
                insumo_id=insumo_id, tipo='ENTRADA', quantidade=qtd,
                observacao="Entrada de compra no depósito", gestor=request.user
            )
            mensagem = f"Entrada de +{qtd} adicionada ao Estoque Principal!"

        elif acao == 'editar_saldo':
            est_principal.quantidade_atual = qtd
            est_principal.save()
            MovimentacaoEstoquePrincipal.objects.create(
                insumo_id=insumo_id, tipo='AJUSTE', quantidade=qtd,
                observacao="Edição manual de saldo", gestor=request.user
            )
            mensagem = f"Saldo ajustado manualmente para {qtd}!"

    itens_estoque = EstoquePrincipal.objects.filter(gestor=request.user).select_related('insumo')
    if busca:
        itens_estoque = itens_estoque.filter(insumo__nome_insumo__icontains=busca)

    return render(request, 'estoque_principal.html', {
        'itens_estoque': itens_estoque,
        'busca': busca,
        'mensagem': mensagem
    })


@login_required
def gestao_equipe_view(request):
    if not request.user.is_superuser:
        return redirect('contagem_mobile')

    mensagem = None
    erro = None

    if request.method == 'POST':
        acao = request.POST.get('acao')

        if acao == 'criar_usuario':
            username = request.POST.get('novo_username').strip()
            senha = request.POST.get('nova_senha')
            if User.objects.filter(username=username).exists():
                erro = f"O usuário '{username}' já existe."
            else:
                novo_user = User.objects.create_user(username=username, password=senha)
                PerfilFuncionario.objects.create(usuario=novo_user, gestor=request.user)
                mensagem = f"Responsável '{username}' criado!"

        elif acao == 'criar_setor':
            nome_setor = request.POST.get('nome_setor')
            responsavel_id = request.POST.get('responsavel_id')
            insumos_ids = request.POST.getlist('insumos_selecionados')

            if not insumos_ids:
                erro = "Selecione pelo menos um insumo para controlar neste setor."
            else:
                responsavel = get_object_or_404(User, id=responsavel_id)
                setor = SetorEstoque.objects.create(
                    nome_setor=nome_setor, responsavel=responsavel, gestor=request.user
                )
                setor.insumos.set(insumos_ids)
                mensagem = f"Setor '{nome_setor}' atribuído para {responsavel.username}!"

    return render(request, 'gestao_equipe.html', {
        'funcionarios': User.objects.filter(perfil_funcionario__gestor=request.user),
        'insumos': Insumo.objects.filter(usuario=request.user),
        'setores': SetorEstoque.objects.filter(gestor=request.user),
        'mensagem': mensagem,
        'erro': erro
    })


@login_required
def contagem_mobile_view(request):
    setor = SetorEstoque.objects.filter(responsavel=request.user, ativo=True).first()
    hoje = timezone.localdate()
    sucesso = None

    if request.method == 'POST' and setor:
        for insumo in setor.insumos.all():
            ent_str = request.POST.get(f'entrada_{insumo.id}', '').replace(',', '.')
            sai_str = request.POST.get(f'saida_{insumo.id}', '').replace(',', '.')
            rep_str = request.POST.get(f'reposicao_{insumo.id}', '0').replace(',', '.')

            if ent_str:
                entrada = Decimal(ent_str)
                saida = Decimal(sai_str) if sai_str else None
                reposicao = Decimal(rep_str) if rep_str else Decimal('0')

                contagem, criado = ContagemDiariaSetor.objects.get_or_create(
                    setor=setor, insumo=insumo, data_contagem=hoje,
                    defaults={
                        'qtd_entrada': entrada, 'qtd_saida': saida,
                        'qtd_reposicao': reposicao, 'responsavel': request.user
                    }
                )
                if not criado:
                    contagem.qtd_entrada = entrada
                    contagem.qtd_saida = saida
                    contagem.qtd_reposicao = reposicao
                    contagem.save()

        sucesso = "Contagem salva! Consumo registrado e reposição abatida do Estoque Principal."

    itens_tela = []
    if setor:
        for insumo in setor.insumos.all():
            reg = ContagemDiariaSetor.objects.filter(setor=setor, insumo=insumo, data_contagem=hoje).first()
            itens_tela.append({
                'insumo': insumo,
                'entrada': reg.qtd_entrada if reg else '',
                'saida': reg.qtd_saida if reg and reg.qtd_saida is not None else '',
                'reposicao': reg.qtd_reposicao if reg and reg.qtd_reposicao > 0 else '',
                'consumo_real': reg.consumo_real if reg else 0
            })

    return render(request, 'contagem_mobile.html', {
        'setor': setor, 'itens_tela': itens_tela, 'hoje': hoje, 'sucesso': sucesso
    })
