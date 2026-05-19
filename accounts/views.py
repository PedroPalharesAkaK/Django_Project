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