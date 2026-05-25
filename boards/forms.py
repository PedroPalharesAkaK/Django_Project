from django import forms
from .models import Avaliacao, Comentario

class NewAvaliacaoForm(forms.ModelForm):
    # Usamos 'texto' em vez de 'message' para ligar com o modelo Comentario
    texto = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Qual a sua opinião sobre o professor?'}), 
        max_length=4000,
        help_text='O tamanho máximo do texto é 4000 caracteres.'
    )

    class Meta:
        model = Avaliacao
        fields = ['titulo', 'texto'] # 'subject' virou 'titulo'

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto',] # 'message' virou 'texto'
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Escreva seu comentário aqui...'})
        }