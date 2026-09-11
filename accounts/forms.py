from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User

class SignUpForm(UserCreationForm):
    email = forms.CharField(max_length=254, required=True, widget=forms.EmailInput())
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2')

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('Já existe uma conta cadastrada com este e-mail.')
        return email


class EmailOrUsernameAuthenticationForm(AuthenticationForm):
    """Permite fazer login informando o nome de usuário OU o e-mail cadastrado."""
    username = forms.CharField(label='Usuário ou e-mail')


from .models import Perfil

# Formulário para os dados nativos do Django (caso ele queira mudar o email principal ou nome)
class UserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email']

    def clean_email(self):
        email = self.cleaned_data['email']
        if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError('Já existe uma conta cadastrada com este e-mail.')
        return email

# Formulário para os dados de estudante
class PerfilUpdateForm(forms.ModelForm):
    class Meta:
        model = Perfil
        fields = ['instituto', 'curso', 'semestre_ingresso', 'email_institucional', 'bio']