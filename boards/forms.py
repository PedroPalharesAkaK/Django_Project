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
        choices=NOTAS_CHOICES, coerce=int, widget=forms.RadioSelect, label='Amor por dar Aula' #Os testes usam o nome nota_empenho
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



from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.template.defaultfilters import filesizeformat
from django.utils import timezone

from .models import Contato, Disciplina, ProvaAntiga
from .provas import preparar_arquivo, semestres_ate_hoje


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """FileField que aceita vários arquivos (receita da documentação do Django)."""
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('widget', MultipleFileInput())
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        if not data:
            raise ValidationError(self.error_messages['required'], code='required')
        arquivos = data if isinstance(data, (list, tuple)) else [data]
        return [super(MultipleFileField, self).clean(arquivo, initial) for arquivo in arquivos]


class ProvaAntigaForm(forms.Form):
    disciplina = forms.CharField(
        label='Disciplina', max_length=300,
        widget=forms.TextInput(attrs={
            'list': 'disciplinas-sugeridas', 'autocomplete': 'off', 'spellcheck': 'false',
            'placeholder': 'Código ou nome, ex.: MAT0111 ou Cálculo',
        }),
    )
    semestre = forms.ChoiceField(label='Semestre')
    tipo = forms.ChoiceField(label='Prova', choices=ProvaAntiga.TIPOS, widget=forms.RadioSelect)
    observacao = forms.CharField(
        label='Observação', required=False, max_length=200,
        widget=forms.TextInput(attrs={'placeholder': 'Opcional. Ex.: turma do noturno, com gabarito'}),
    )
    arquivos = MultipleFileField(
        label='Fotos ou PDF da prova',
        widget=MultipleFileInput(attrs={'accept': 'application/pdf,image/jpeg,image/png'}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields['semestre'].choices = [('', 'Selecione')] + [(s, s) for s in semestres_ate_hoje()]

    def clean_disciplina(self):
        valor = self.cleaned_data['disciplina'].strip()
        # As sugestões vêm como "MAT0111 - Cálculo...": o código é a primeira palavra
        codigo = valor.split()[0].upper() if valor else ''
        disciplina = Disciplina.objects.filter(codigo=codigo).first()
        if disciplina is None:
            raise ValidationError('Escolha uma disciplina da lista: digite o código (ex.: MAT0111) ou parte do nome.')
        return disciplina

    def clean_arquivos(self):
        arquivos = self.cleaned_data['arquivos']
        if len(arquivos) > settings.PROVAS_MAX_ARQUIVOS:
            raise ValidationError(f'Envie no máximo {settings.PROVAS_MAX_ARQUIVOS} arquivos por prova.')
        total = sum(arquivo.size for arquivo in arquivos)
        if total > settings.PROVAS_TAMANHO_MAXIMO:
            raise ValidationError(
                f'Os arquivos somam {filesizeformat(total)}; o limite é {filesizeformat(settings.PROVAS_TAMANHO_MAXIMO)}. '
                'Envie menos páginas ou fotos com resolução menor.'
            )
        preparados, erros = [], []
        for arquivo in arquivos:
            try:
                preparados.append(preparar_arquivo(arquivo))
            except ValidationError as erro:
                erros.extend(erro.messages)
        if erros:
            raise ValidationError(erros)
        return preparados

    def clean(self):
        cleaned_data = super().clean()
        if self.user is not None:
            desde = timezone.now() - timedelta(days=1)
            enviadas = ProvaAntiga.objects.filter(enviado_por=self.user, criado_em__gte=desde).count()
            if enviadas >= settings.PROVAS_LIMITE_DIARIO:
                raise ValidationError(
                    f'Você já enviou {enviadas} provas nas últimas 24 horas, o limite diário. Tente de novo amanhã.'
                )
        return cleaned_data


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