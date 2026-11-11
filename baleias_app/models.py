from django.db import models
from django.contrib.auth.models import User

# tabela de insumos
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
    custo = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Custo ")
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
        verbose_name="Preço Unitário"
    )
    data_cadastro_insumo = models.DateField(auto_now_add=True, verbose_name="Data de Cadastro")
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Usuário")
    quantidade_estoque = models.DecimalField(
        max_digits=10, 
        decimal_places=3, 
        default=0, 
        verbose_name="Quantidade em Estoque"
    )
    # dividi o custo pela quantidade 
    def save(self, *args, **kwargs):
        if self.quantidade_unitaria and self.quantidade_unitaria > 0:
            self.preco_unitario = self.custo / self.quantidade_unitaria
        else:
            self.preco_unitario = 0
        super().save(*args, **kwargs)
    #garante o nome da tabela
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
