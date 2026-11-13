from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home_view, name='home'),
    path('insumos/cadastrar/', views.cadastrar_insumo_view, name='cadastrar_insumo'),
    path('estoque-principal/', views.estoque_principal_view, name='estoque_principal'),
    path('equipe/', views.gestao_equipe_view, name='gestao_equipe'),
    path('contagem/', views.contagem_mobile_view, name='contagem_mobile'),
]
