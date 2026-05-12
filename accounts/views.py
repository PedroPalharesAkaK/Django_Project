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