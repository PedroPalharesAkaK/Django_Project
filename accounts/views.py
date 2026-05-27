from django.contrib.auth import login as auth_login
# Remova: from django.contrib.auth.forms import UserCreationForm
from .forms import SignUpForm  # Importe o seu novo formulário
from django.shortcuts import render, redirect

def signup(request):
    if request.method == 'POST':
        form = SignUpForm(request.POST) # Use o SignUpForm aqui
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            return redirect('home')
    else:
        form = SignUpForm() # E aqui também
    return render(request, 'signup.html', {'form': form})

# accounts/views.py

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView

# ... suas views anteriores de signup ...

@method_decorator(login_required, name='dispatch')
class UserUpdateView(UpdateView):
    model = User
    fields = ('first_name', 'last_name', 'email', )
    template_name = 'my_account.html'
    success_url = reverse_lazy('my_account')

    def get_object(self):
        # Retorna sempre o usuário logado atualmente
        return self.request.user
    
@login_required
def meu_perfil(request):
    # O Django já manda o request.user automaticamente para o template, 
    # então só precisamos renderizar a página.
    return render(request, 'meu_perfil.html')

# accounts/views.py


from django.contrib import messages
from .forms import UserUpdateForm, PerfilUpdateForm

@login_required
def editar_perfil(request):
    if request.method == 'POST':
        # Instancia os formulários com os dados enviados (POST) e diz de quem são (instance)
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = PerfilUpdateForm(request.POST, instance=request.user.perfil)
        
        # Se os dois formulários forem válidos, salva no banco de dados
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, 'O seu perfil foi atualizado com sucesso!')
            return redirect('meu_perfil') # Redireciona de volta para ver como ficou
            
    else:
        # Se for um GET (apenas abrir a página), carrega os formulários preenchidos com os dados atuais
        u_form = UserUpdateForm(instance=request.user)
        p_form = PerfilUpdateForm(instance=request.user.perfil)

    # Envia os dois formulários para o template
    context = {
        'u_form': u_form,
        'p_form': p_form
    }
    
    return render(request, 'editar_perfil.html', context)