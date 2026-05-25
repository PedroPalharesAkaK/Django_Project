"""
URL configuration for ProjetoDjanto project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from boards import views
from accounts import views as accounts_views
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.ProfessorListView.as_view(), name='home'),
    path('signup/', accounts_views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='login.html'), name='login'), #temporario
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    
    # NOVAS ROTAS PARA PROFESSORES E AVALIAÇÕES
    path('professores/<int:pk>/', views.AvaliacaoListView.as_view(), name='professor_avaliacoes'),
    path('professores/<int:pk>/new/', views.new_avaliacao, name='new_avaliacao'),
    path('about/', views.about, name='about'),
    path('professores/<int:pk>/avaliacoes/<int:avaliacao_pk>/', views.ComentarioListView.as_view(), name='avaliacao_comentarios'),
    path('professores/<int:pk>/avaliacoes/<int:avaliacao_pk>/reply/', views.reply_avaliacao, name='reply_avaliacao'),
    
    # Rotas de Reset de Password (Intactas)
    path('reset/', auth_views.PasswordResetView.as_view(
             template_name='password_reset.html',
             email_template_name='password_reset_email.html',
             subject_template_name='password_reset_subject.txt'
         ), name='password_reset'),
    path('reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='password_reset_confirm.html'), name='password_reset_confirm'),
    path('reset/complete/', auth_views.PasswordResetCompleteView.as_view(template_name='password_reset_complete.html'), name='password_reset_complete'),
    path('settings/password/', auth_views.PasswordChangeView.as_view(template_name='password_change.html'), name='password_change'),
    path('settings/password/done/', auth_views.PasswordChangeDoneView.as_view(template_name='password_change_done.html'), name='password_change_done'),
    
    # Rota de edição de comentário atualizada
    path('professores/<int:pk>/avaliacoes/<int:avaliacao_pk>/comentarios/<int:comentario_pk>/edit/', 
         views.ComentarioUpdateView.as_view(), 
         name='edit_comentario'),

    path('settings/account/', accounts_views.UserUpdateView.as_view(), name='my_account'),
]