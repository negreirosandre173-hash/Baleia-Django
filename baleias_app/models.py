from django.db import models
from django.db.models import Avg
from django.contrib.auth.models import User


class Insumo(models.Model):
    UNIDADES_CHOICES = [
        ('G', 'G (Gramas)'),
        ('ML', 'ML (Mililitros)'),
        ('UNID', 'UNID (Unidade)'),
    ]

    nome_insumo = models.CharField(max_length=100, verbose_name="Nome do Insumo")
    unidade_de_medida = models.CharField(max_length=4, choices=UNIDADES_CHOICES, verbose_name="Unidade de Medida")
    custo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Custo Atual (R$)")
    fornecedor = models.CharField(max_length=100, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    quantidade_unitaria = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Quantidade Unitária")
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=4, editable=False, default=0)
    data_cadastro_insumo = models.DateField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    @property
    def media_custo_historico(self):
        resultado = self.historicos.aggregate(media=Avg('valor_custo'))['media']
        return round(resultado, 2) if resultado else self.custo

    def save(self, *args, **kwargs):
        if self.quantidade_unitaria and self.quantidade_unitaria > 0:
            self.preco_unitario = self.custo / self.quantidade_unitaria
        else:
            self.preco_unitario = 0

        is_novo = self.pk is None
        custo_mudou = False
        if not is_novo:
            insumo_antigo = Insumo.objects.get(pk=self.pk)
            if insumo_antigo.custo != self.custo:
                custo_mudou = True

        super().save(*args, **kwargs)

        if is_novo or custo_mudou:
            HistoricoCustoInsumo.objects.create(insumo=self, valor_custo=self.custo, usuario=self.usuario)
            historicos = self.historicos.order_by('-data_registro', '-id')
            if historicos.count() > 3:
                ids_manter = historicos.values_list('id', flat=True)[:3]
                self.historicos.exclude(id__in=ids_manter).delete()

    class Meta:
        db_table = 'insumos'

    def __str__(self):
        return f"{self.nome_insumo} ({self.unidade_de_medida})"


class HistoricoCustoInsumo(models.Model):
    insumo = models.ForeignKey(Insumo, related_name='historicos', on_delete=models.CASCADE)
    valor_custo = models.DecimalField(max_digits=10, decimal_places=2)
    data_registro = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'historico_custos_insumos'


# --- 1. ESTOQUE PRINCIPAL (DEPÓSITO CENTRAL) ---
class EstoquePrincipal(models.Model):
    insumo = models.OneToOneField(Insumo, on_delete=models.CASCADE, related_name='estoque_principal')
    quantidade_atual = models.DecimalField(max_digits=10, decimal_places=3, default=0)
    ultima_atualizacao = models.DateTimeField(auto_now=True)
    gestor = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'estoque_principal'

    def __str__(self):
        return f"Principal: {self.insumo.nome_insumo} ({self.quantidade_atual})"


class MovimentacaoEstoquePrincipal(models.Model):
    """Guarda todo histórico de entradas de compras e edições manuais no Principal"""
    TIPOS_CHOICES = [
        ('ENTRADA', 'Entrada de Compra'),
        ('AJUSTE', 'Ajuste / Edição Manual'),
        ('REPOSICAO', 'Saída para Reposição de Setor'),
    ]
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE)
    tipo = models.CharField(max_length=15, choices=TIPOS_CHOICES)
    quantidade = models.DecimalField(max_digits=10, decimal_places=3)
    observacao = models.CharField(max_length=200, blank=True, null=True)
    data_movimento = models.DateTimeField(auto_now_add=True)
    gestor = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'movimentacoes_principal'


# --- 2. SETORES DE ESTOQUE (BAR, COZINHA, ETC.) ---
class PerfilFuncionario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE, related_name='perfil_funcionario')
    gestor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meus_funcionarios')

    class Meta:
        db_table = 'perfis_funcionarios'


class SetorEstoque(models.Model):
    nome_setor = models.CharField(max_length=100, verbose_name="Nome do Setor (Ex: Estoque Bar, Cozinha)")
    responsavel = models.ForeignKey(User, on_delete=models.CASCADE, related_name='setores_gerenciados')
    gestor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='setores_criados')
    insumos = models.ManyToManyField(Insumo, related_name='setores_vinculados')
    ativo = models.BooleanField(default=True)

    class Meta:
        db_table = 'setores_estoque'

    def __str__(self):
        return f"{self.nome_setor} (Resp: {self.responsavel.username})"


# --- 3. CONTAGEM DIÁRIA, CONSUMO REAL E REPOSIÇÃO ---
class ContagemDiariaSetor(models.Model):
    """Tabela analítica: guarda data, entrada, saída, consumo real e reposição para futuros dashboards"""
    setor = models.ForeignKey(SetorEstoque, on_delete=models.CASCADE, related_name='contagens')
    insumo = models.ForeignKey(Insumo, on_delete=models.CASCADE)
    
    qtd_entrada = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Contagem Inicial (Entrada)")
    qtd_saida = models.DecimalField(max_digits=10, decimal_places=3, blank=True, null=True, verbose_name="Contagem Final (Saída)")
    
    # Campo calculado e salvo no banco para consultas rápidas de média e curva ABC no futuro
    consumo_real = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name="Saída/Venda Real")
    
    # Terceiro campo do formulário mobile: quanto o funcionário repôs do Estoque Principal
    qtd_reposicao = models.DecimalField(max_digits=10, decimal_places=3, default=0, verbose_name="Reposição Retirada do Principal")
    
    data_contagem = models.DateField(auto_now_add=True)
    responsavel = models.ForeignKey(User, on_delete=models.CASCADE)

    def save(self, *args, **kwargs):
        # 1. Calcula automaticamente o consumo/venda do dia (Ex: 50 - 40 = 10)
        if self.qtd_saida is not None:
            self.consumo_real = self.qtd_entrada - self.qtd_saida
        else:
            self.consumo_real = 0

        # 2. Controla o abatimento no Estoque Principal caso haja reposição
        reposicao_anterior = 0
        if self.pk:
            registro_antigo = ContagemDiariaSetor.objects.get(pk=self.pk)
            reposicao_anterior = registro_antigo.qtd_reposicao

        diferenca_reposicao = self.qtd_reposicao - reposicao_anterior

        if diferenca_reposicao != 0:
            est_principal, _ = EstoquePrincipal.objects.get_or_create(
                insumo=self.insumo, 
                defaults={'gestor': self.setor.gestor}
            )
            est_principal.quantidade_atual -= diferenca_reposicao
            est_principal.save()

            # Registra no histórico do principal para rastreabilidade
            MovimentacaoEstoquePrincipal.objects.create(
                insumo=self.insumo,
                tipo='REPOSICAO',
                quantidade=-diferenca_reposicao,
                observacao=f"Reposição para {self.setor.nome_setor} por {self.responsavel.username}",
                gestor=self.setor.gestor
            )

        super().save(*args, **kwargs)

    class Meta:
        db_table = 'contagens_diarias_setor'
        ordering = ['-data_contagem', 'insumo__nome_insumo']
