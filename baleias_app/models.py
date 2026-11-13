from django.db import models
from django.db.models import Avg  # Importa a função nativa de média
from django.contrib.auth.models import User


class Insumo(models.Model):
    UNIDADES_CHOICES = [
        ('G', 'G (Gramas)'),
        ('ML', 'ML (Mililitros)'),
        ('UNID', 'UNID (Unidade)'),
    ]

    nome_insumo = models.CharField(max_length=100, verbose_name="Nome do Insumo")
    unidade_de_medida = models.CharField(
        max_length=4,
        choices=UNIDADES_CHOICES,
        verbose_name="Unidade de Medida"
    )
    custo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Custo Atual (R$)")
    fornecedor = models.CharField(max_length=100, blank=True, null=True)
    telefone = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(max_length=100, blank=True, null=True)
    quantidade_unitaria = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        verbose_name="Quantidade Unitária"
    )
    preco_unitario = models.DecimalField(
        max_digits=10, 
        decimal_places=4, 
        editable=False, 
        default=0,
        verbose_name="Preço Unitário Atual (R$)"
    )
    data_cadastro_insumo = models.DateField(auto_now_add=True, verbose_name="Data de Cadastro")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    quantidade_estoque = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        default=0, 
        verbose_name="Quantidade em Estoque"
    )

    # Calcula a média automática dos últimos 1, 2 ou 3 valores no histórico
    @property
    def media_custo_historico(self):
        resultado = self.historicos.aggregate(media=Avg('valor_custo'))['media']
        return round(resultado, 2) if resultado else self.custo

    def save(self, *args, **kwargs):
        # 1. Calcula o preço unitário do custo atual
        if self.quantidade_unitaria and self.quantidade_unitaria > 0:
            self.preco_unitario = self.custo / self.quantidade_unitaria
        else:
            self.preco_unitario = 0

        # 2. Verifica se é um cadastro novo ou se o custo mudou na edição
        is_novo = self.pk is None
        custo_mudou = False

        if not is_novo:
            insumo_antigo = Insumo.objects.get(pk=self.pk)
            if insumo_antigo.custo != self.custo:
                custo_mudou = True

        # Salva o insumo primeiro para garantir que ele tenha um ID
        super().save(*args, **kwargs)

        # 3. Se for novo ou se o preço mudou, registra no histórico e limita a 3 itens
        if is_novo or custo_mudou:
            HistoricoCustoInsumo.objects.create(
                insumo=self,
                valor_custo=self.custo,
                usuario=self.usuario
            )
            
            # Busca os históricos ordenados do mais novo para o mais antigo
            historicos = self.historicos.order_by('-data_registro', '-id')
            if historicos.count() > 3:
                # Apaga todos que ficarem da 4ª posição em diante
                ids_para_manter = historicos.values_list('id', flat=True)[:3]
                self.historicos.exclude(id__in=ids_para_manter).delete()

    class Meta:
        db_table = 'insumos'
        verbose_name = 'Insumo'
        verbose_name_plural = 'Insumos'

    def __str__(self):
        return f"{self.nome_insumo} ({self.unidade_de_medida})"


class Produto(models.Model):
    nome_produto = models.CharField(max_length=100, verbose_name="Nome do Produto")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")

    @property
    def custo_total_receita(self):
        # Soma automaticamente o custo de todos os insumos ligados a este produto
        return sum(item.custo_proporcional for item in self.itens.all())

    class Meta:
        db_table = 'produtos'
        verbose_name = 'Produto'
        verbose_name_plural = 'Produtos'

    def __str__(self):
        return self.nome_produto


class ItemProduto(models.Model):
    produto = models.ForeignKey(Produto, related_name='itens', on_delete=models.CASCADE)
    insumo_usado = models.ForeignKey(Insumo, on_delete=models.PROTECT, verbose_name="Insumo Usado")
    quantidade_insumo_usada = models.DecimalField(max_digits=10, decimal_places=3, verbose_name="Quantidade Usada")

    @property
    def custo_proporcional(self):
        return self.insumo_usado.preco_unitario * self.quantidade_insumo_usada

    class Meta:
        db_table = 'itens_produto'


class HistoricoCustoInsumo(models.Model):
    insumo = models.ForeignKey(
        Insumo, 
        related_name='historicos', 
        on_delete=models.CASCADE,
        verbose_name="Insumo"
    )
    valor_custo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Custo Registrado (R$)")
    data_registro = models.DateTimeField(auto_now_add=True, verbose_name="Data do Registro")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")

    class Meta:
        db_table = 'historico_custos_insumos'
        verbose_name = 'Histórico de Custo'
        verbose_name_plural = 'Histórico de Custos'
        ordering = ['-data_registro', '-id']

    def __str__(self):
        return f"{self.insumo.nome_insumo} - R$ {self.valor_custo}"