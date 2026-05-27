from django import forms
from .models import Avaliacao, Comentario

class NewAvaliacaoForm(forms.ModelForm):
    # Definimos as escolhas possíveis (0, 1, 2, 3, 4, 5)
    NOTAS_CHOICES = [(i, str(i)) for i in range(6)]

    # Transformamos os campos numéricos em Radio Buttons para facilitar o clique
    nota_geral = forms.TypedChoiceField(
        choices=NOTAS_CHOICES, coerce=int, widget=forms.RadioSelect, label='Avaliação Geral'
    )
    nota_didatica = forms.TypedChoiceField(
        choices=NOTAS_CHOICES, coerce=int, widget=forms.RadioSelect, label='Didática'
    )
    nota_empenho = forms.TypedChoiceField(
        choices=NOTAS_CHOICES, coerce=int, widget=forms.RadioSelect, label='Empenho/Dedicação'
    )
    nota_relacao = forms.TypedChoiceField(
        choices=NOTAS_CHOICES, coerce=int, widget=forms.RadioSelect, label='Relação com os alunos'
    )
    nota_dificuldade = forms.TypedChoiceField(
        choices=NOTAS_CHOICES, coerce=int, widget=forms.RadioSelect, label='Dificuldade'
    )

    texto = forms.CharField(
        widget=forms.Textarea(attrs={'rows': 5, 'placeholder': 'Qual a sua opinião sobre o professor?'}), 
        max_length=4000,
        help_text='O tamanho máximo do texto é 4000 caracteres.',
        label='Comentário'
    )

    class Meta:
        model = Avaliacao
        # Agora dizemos ao Django para incluir todos os campos novos na página de criação!
        fields = [
            'titulo', 
            'nota_geral', 
            'nota_didatica', 
            'nota_empenho', 
            'nota_relacao', 
            'nota_dificuldade', 
            'texto'
        ]

class ComentarioForm(forms.ModelForm):
    class Meta:
        model = Comentario
        fields = ['texto',] 
        widgets = {
            'texto': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Escreva a sua resposta aqui...'})
        }



from .models import Contato

class ContatoForm(forms.ModelForm):
    class Meta:
        model = Contato
        fields = ['nome', 'sobrenome', 'email', 'mensagem']
        
        # Isto aplica a classe 'form-control' do Bootstrap nas caixas de texto
        widgets = {
            'nome': forms.TextInput(attrs={'class': 'form-control'}),
            'sobrenome': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'mensagem': forms.Textarea(attrs={'class': 'form-control', 'rows': 5}),
        }