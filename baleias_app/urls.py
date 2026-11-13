from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('', views.home_view, name='home'),
    path('insumos/cadastrar/', views.cadastrar_insumo_view, name='cadastrar_insumo'),
]
