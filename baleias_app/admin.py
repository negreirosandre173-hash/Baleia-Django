from django.contrib import admin
from .models import (
    Insumo, HistoricoCustoInsumo, EstoquePrincipal, 
    MovimentacaoEstoquePrincipal, SetorEstoque, ContagemDiariaSetor
)

admin.site.register(Insumo)
admin.site.register(HistoricoCustoInsumo)
admin.site.register(EstoquePrincipal)
admin.site.register(MovimentacaoEstoquePrincipal)
admin.site.register(SetorEstoque)
admin.site.register(ContagemDiariaSetor)
