from django.contrib import admin
from .models import Insumo, Produto, ItemProduto, HistoricoCustoInsumo


@admin.register(Insumo)
class InsumoAdmin(admin.ModelAdmin):
    # Adiciona 'media_custo_historico' na tabela principal
    list_display = (
        'id', 'nome_insumo', 'unidade_de_medida', 'custo', 
        'media_custo_historico', 'quantidade_unitaria', 'preco_unitario', 
        'quantidade_estoque', 'usuario'
    )
    readonly_fields = ('preco_unitario', 'media_custo_historico', 'data_cadastro_insumo')
    exclude = ('usuario',)
    search_fields = ('nome_insumo',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(usuario=request.user)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)


class ItemProdutoInline(admin.TabularInline):
    model = ItemProduto
    extra = 1 # deixa 1 linha pronta para preencher
    autocomplete_fields = ('insumo_usado',)
    readonly_fields = ('custo_proporcional',)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "insumo_usado" and not request.user.is_superuser:
            kwargs["queryset"] = Insumo.objects.filter(usuario=request.user)
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


@admin.register(Produto)
class ProdutoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nome_produto', 'custo_total_receita', 'usuario')
    readonly_fields = ('custo_total_receita',)
    inlines = [ItemProdutoInline]
    exclude = ('usuario',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(usuario=request.user)

    def save_model(self, request, obj, form, change):
        if not change:
            obj.usuario = request.user
        super().save_model(request, obj, form, change)


@admin.register(HistoricoCustoInsumo)
class HistoricoCustoInsumoAdmin(admin.ModelAdmin):
    list_display = ('id', 'insumo', 'valor_custo', 'data_registro', 'usuario')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs if request.user.is_superuser else qs.filter(usuario=request.user)

    # Bloqueia criação, edição e exclusão manual para manter a integridade da média
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False