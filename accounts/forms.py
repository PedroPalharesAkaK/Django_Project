from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.CharField(max_length=254, required=True, widget=forms.EmailInput())
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')


from .models import Perfil

# Formulário para os dados nativos do Django (caso ele queira mudar o email principal ou nome)
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

# Formulário para os dados de estudante
class PerfilUpdateForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['instituto', 'curso', 'semestre_ingresso', 'email_institucional', 'bio']