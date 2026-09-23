from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Professor, Avaliacao, Comentario, Disciplina, ProvaAntiga, ArquivoProva
from .forms import NewAvaliacaoForm, ComentarioForm, ProvaAntigaForm
from .provas import salvar_arquivos
from .utils import normalizar
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction # Adicione este import
from django.http import FileResponse, Http404, JsonResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView
from django.db.models import Count, Avg, Q, Case, When, Value, IntegerField
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger 
from django.db.models import F
from django.views.decorators.cache import never_cache
from django.contrib import messages


class ProfessorListView(ListView):
    model = Professor
    context_object_name = 'professors' 
    template_name = 'home.html'
    paginate_by = 20

    def get_queryset(self):
        queryset = super().get_queryset()
        
        # 1. Filtro de Pesquisa por Texto
        query = self.request.GET.get('q')
        if query:
            queryset = queryset.filter(nome__icontains=query)
            
        # 2. Filtro de Ordenação (Atualizado)
        sort = self.request.GET.get('sort')
        
        if sort == 'visualizacoes':
            # Ordena pelos professores mais vistos
            queryset = queryset.order_by('-visualizacoes')
            
        elif sort == 'avaliacoes':
            # Conta quantas avaliações cada professor tem e ordena do maior para o menor
            queryset = queryset.annotate(total_avaliacoes=Count('avaliacoes')).order_by('-total_avaliacoes')
            
        elif sort == 'alfabetica':
            # A ordem alfabética agora passa a ser ativada apenas se escolhida no menu
            queryset = queryset.order_by('nome')
            
        else:
            # PADRÃO ABSOLUTO: Se não houver filtro (página inicial), traz a Maior Nota Geral
            # O F().desc(nulls_last=True) empurra quem não tem nota para o final
            # Precisa ignorar avaliações com excluir_da_media=True (ex: comentários
            # importados sem nota real), senão essa média diverge da exibida na tela
            # (Professor.get_media_geral() já faz esse filtro).
            queryset = queryset.annotate(
                media_db=Avg('avaliacoes__nota_geral', filter=Q(avaliacoes__excluir_da_media=False))
            ).order_by(F('media_db').desc(nulls_last=True))

        return queryset

class AvaliacaoListView(ListView):
    model = Professor
    context_object_name = 'avaliacoes'
    template_name = 'avaliacoes.html'
    paginate_by = 20

    def get_queryset(self):
        self.professor = get_object_or_404(Professor, pk=self.kwargs.get('pk'))
        queryset = self.professor.avaliacoes.order_by('-last_updated').annotate(replies=Count('comentarios') - 1)
        return queryset

    # ---> SUBSTITUA TODA ESTA FUNÇÃO <---
    def get_context_data(self, **kwargs):
        # 1. LÓGICA DO CONTADOR DE VISUALIZAÇÕES
        session_key = f'viewed_professor_{self.professor.pk}'
        
        # Se o utilizador ainda não visitou este professor nesta sessão, soma +1
        if not self.request.session.get(session_key, False):
            self.professor.visualizacoes += 1
            self.professor.save()
            # Marca que já visitou para não somar de novo ao recarregar a página
            self.request.session[session_key] = True

        # 2. CÓDIGO ORIGINAL QUE VOCÊ JÁ TINHA
        kwargs['professor'] = self.professor
        kwargs['aba'] = 'avaliacoes'
        
        # Se o utilizador estiver logado, verifica se já existe uma avaliação dele
        if self.request.user.is_authenticated:
            kwargs['usuario_ja_avaliou'] = Avaliacao.objects.filter(
                professor=self.professor,
                starter=self.request.user
            ).exists()
        else:
            # Visitante sem login: só sabemos se já avaliou anonimamente nesta sessão
            kwargs['usuario_ja_avaliou'] = self.request.session.get(
                anonimo_session_key(self.professor.pk), False
            )
            
        return super().get_context_data(**kwargs)

# Pode apagar ou comentar a antiga 'def avaliacao_comentarios' e colar esta no lugar:
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.db.models import F  # Import necessário para incrementar de forma segura
from .models import Avaliacao, Comentario

class ComentarioListView(ListView):
    model = Comentario
    context_object_name = 'comentarios'
    template_name = 'avaliacao_comentarios.html'
    paginate_by = 20

    def get_context_data(self, **kwargs):
        # Cria uma chave única na sessão do utilizador para este tópico específico
        session_key = f'viewed_avaliacao_{self.avaliacao.pk}'

        # Se esta chave não existir (False), significa que é a primeira visita
        if not self.request.session.get(session_key, False):
            self.avaliacao.views += 1
            self.avaliacao.save()
            # Marca a chave como True para que futuras visitas não somem +1
            self.request.session[session_key] = True

        kwargs['avaliacao'] = self.avaliacao
        return super().get_context_data(**kwargs)

    def get_queryset(self):
        # Vai buscar o tópico à base de dados para podermos listar os comentarios
        self.avaliacao = get_object_or_404(Avaliacao, professor__pk=self.kwargs.get('pk'), pk=self.kwargs.get('avaliacao_pk')) #os dois pk tem q existir
        queryset = self.avaliacao.comentarios.order_by('created_at')
        return queryset


def anonimo_session_key(professor_pk):
    return f'avaliou_anonimo_{professor_pk}'


# Sem @login_required: visitantes sem conta também podem avaliar. A avaliação fica
# sem autor (starter/created_by = None) e aparece marcada como de conta não verificada.
@never_cache
def new_avaliacao(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    anonimo = not request.user.is_authenticated

    # Verifica se já avaliou (para anônimos, só dá para saber pela sessão)
    if anonimo:
        ja_avaliou = request.session.get(anonimo_session_key(professor.pk), False)
    else:
        ja_avaliou = Avaliacao.objects.filter(professor=professor, starter=request.user).exists()
    if ja_avaliou:
        return redirect('professor_avaliacoes', pk=professor.pk)

    if request.method == 'POST':
        form = NewAvaliacaoForm(request.POST)
        if form.is_valid():
            autor = None if anonimo else request.user

            avaliacao = form.save(commit=False)
            avaliacao.professor = professor
            avaliacao.starter = autor
            avaliacao.save()

            Comentario.objects.create(
                texto=form.cleaned_data.get('texto'),
                avaliacao=avaliacao,
                created_by=autor
            )

            if anonimo:
                request.session[anonimo_session_key(professor.pk)] = True
                messages.success(request, 'Sua avaliação anônima foi publicada! Ela aparece marcada como de uma conta não verificada.')
            else:
                messages.success(request, 'Sua avaliação foi publicada com sucesso!')
            return redirect('avaliacao_comentarios', pk=professor.pk, avaliacao_pk=avaliacao.pk)
    else:
        form = NewAvaliacaoForm()
        
    return render(request, 'new_avaliacao.html', {'professor': professor, 'form': form})

     
    
@login_required
def reply_avaliacao(request, pk, avaliacao_pk):
    avaliacao = get_object_or_404(Avaliacao, professor__pk=pk, pk=avaliacao_pk)
    
    if request.method == 'POST':
        form = ComentarioForm(request.POST)
        if form.is_valid():
            comentario = form.save(commit=False)
            comentario.avaliacao = avaliacao
            comentario.created_by = request.user
            comentario.save()

            avaliacao.last_updated = timezone.now()
            avaliacao.save()

            messages.success(request, 'Sua resposta foi enviada!')
            
            avaliacao_url = reverse('avaliacao_comentarios', kwargs={'pk': pk, 'avaliacao_pk': avaliacao_pk})
            avaliacao_comentario_url = f"{avaliacao_url}?page={avaliacao.get_page_count()}#{comentario.pk}"
            return redirect(avaliacao_comentario_url)
    else:
        form = ComentarioForm()
    return render(request, 'reply_avaliacao.html', {'avaliacao': avaliacao, 'form': form})

#GCBV



@method_decorator(login_required, name='dispatch')
class ComentarioUpdateView(UpdateView):
    model = Comentario
    template_name = 'edit_comentario.html'
    pk_url_kwarg = 'comentario_pk'
    context_object_name = 'comentario'
    def form_valid(self, form):
        comentario = form.save(commit=False)
        comentario.updated_by = self.request.user
        comentario.updated_at = timezone.now()
        comentario.save()
        
        # Adicione esta linha:
        messages.success(self.request, 'Alterações salvas com sucesso!')
        
        return redirect('avaliacao_comentarios', pk=comentario.avaliacao.professor.pk, avaliacao_pk=comentario.avaliacao.pk)

    def get_queryset(self):
        """
        SEGURANÇA PASSO 1: Traz apenas os comentários do utilizador logado.
        """
        return super().get_queryset().filter(created_by=self.request.user)

    def _is_autor_original(self, comentario):
        """
        Função auxiliar de Segurança: Verifica se é o dono da Avaliação E se este 
        é o primeiro comentário (a review original, não uma mera resposta).
        """
        avaliacao = comentario.avaliacao
        primeiro_comentario = avaliacao.comentarios.order_by('created_at').first()
        return self.request.user == avaliacao.starter and comentario == primeiro_comentario

    def get_form_class(self):
        """
        SEGURANÇA PASSO 2: O Camaleão. Escolhe qual formulário carregar.
        """
        comentario = self.get_object()
        if self._is_autor_original(comentario):
            return NewAvaliacaoForm # O formulário completo com Notas!
        return ComentarioForm       # O formulário restrito (só texto)

    def get_form_kwargs(self):
        """
        Preenche os campos antigos na tela para o utilizador poder editar.
        """
        kwargs = super().get_form_kwargs()
        comentario = self.get_object()

        if self._is_autor_original(comentario):
            # Enganamos o formulário para ele ler as notas gravadas na Avaliação
            kwargs['instance'] = comentario.avaliacao
            # E enviamos o texto do comentário à parte
            if 'initial' not in kwargs:
                kwargs['initial'] = {}
            kwargs['initial']['texto'] = comentario.texto
            
        return kwargs

    def form_valid(self, form):
        """
        SEGURANÇA PASSO 3: Gravar as alterações de forma cirúrgica.
        """
        comentario = self.get_object()

        if self._is_autor_original(comentario):
            # 1. Salva as novas notas e título na Avaliação (banco de dados)
            form.save()
            # 2. Atualiza o texto que pertence ao Comentário
            comentario.texto = form.cleaned_data.get('texto')
        else:
            # Comportamento padrão: atualiza só o texto do comentário secundário
            comentario = form.save(commit=False)

        comentario.updated_by = self.request.user
        comentario.updated_at = timezone.now()
        comentario.save()

        # O caminho de volta continua perfeito!
        return redirect('avaliacao_comentarios', pk=comentario.avaliacao.professor.pk, avaliacao_pk=comentario.avaliacao.pk)
    
# Adicione esta função para evitar erros com a rota 'about' do seu urls.py
def about(request):
    return render(request, 'about.html')


from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ContatoForm

def contato(request):
    if request.method == 'POST':
        form = ContatoForm(request.POST)
        if form.is_valid():
            form.save() # Salva a mensagem no banco de dados!
            messages.success(request, 'Sua mensagem foi enviada com sucesso. Obrigado pelo contato!')
            return redirect('home')
    else:
        inicial = {}
        # Link "Pedir remoção" de uma prova antiga já preenche a mensagem
        prova_pk = request.GET.get('remover_prova', '')
        prova = ProvaAntiga.objects.filter(pk=prova_pk).first() if prova_pk.isdigit() else None
        if prova:
            url = request.build_absolute_uri(reverse('prova_detalhe', kwargs={'pk': prova.pk}))
            inicial['mensagem'] = f'Peço a remoção da prova {prova} ({url}).\nMotivo: '
        form = ContatoForm(initial=inicial)

    return render(request, 'contato.html', {'form': form})

from django.views.generic import TemplateView

class QueroAjudarView(TemplateView):
    template_name = 'quero_ajudar.html'


# ---------------------------------------------------------------------------
# Provas antigas
# ---------------------------------------------------------------------------

def provas_professor(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    provas = professor.provas.select_related('disciplina', 'enviado_por').prefetch_related('arquivos')

    por_disciplina = {}
    for prova in provas:
        por_disciplina.setdefault(prova.disciplina, []).append(prova)
    grupos = [
        {'disciplina': disciplina, 'provas': sorted(lista, key=ProvaAntiga.chave_ordenacao)}
        for disciplina, lista in sorted(por_disciplina.items(), key=lambda item: item[0].codigo)
    ]

    return render(request, 'provas_antigas.html', {
        'professor': professor,
        'aba': 'provas',
        'grupos': grupos,
    })


def prova_detalhe(request, pk):
    prova = get_object_or_404(
        ProvaAntiga.objects.select_related('professor', 'disciplina', 'enviado_por').prefetch_related('arquivos'),
        pk=pk,
    )
    return render(request, 'prova_detalhe.html', {
        'prova': prova,
        'professor': prova.professor,
        'pode_excluir': prova.pode_excluir(request.user),
    })


@login_required
def enviar_prova(request, pk):
    professor = get_object_or_404(Professor, pk=pk)

    if request.method == 'POST':
        form = ProvaAntigaForm(request.POST, request.FILES, user=request.user)
        if form.is_valid():
            dados = form.cleaned_data
            with transaction.atomic():
                prova = ProvaAntiga.objects.create(
                    professor=professor,
                    disciplina=dados['disciplina'],
                    semestre=dados['semestre'],
                    tipo=dados['tipo'],
                    observacao=dados['observacao'],
                    enviado_por=request.user,
                )
                salvar_arquivos(prova, dados['arquivos'])
            messages.success(request, 'Prova enviada. Obrigado por ajudar quem vai cursar essa disciplina!')
            return redirect('prova_detalhe', pk=prova.pk)
    else:
        inicial = {}
        # Botão "Enviar prova" de uma disciplina já vem com ela escolhida
        disciplina = Disciplina.objects.filter(codigo=request.GET.get('disciplina', '').upper()).first()
        if disciplina:
            inicial['disciplina'] = f'{disciplina.codigo} - {disciplina.nome}'
        form = ProvaAntigaForm(initial=inicial, user=request.user)

    return render(request, 'enviar_prova.html', {
        'professor': professor,
        'form': form,
        'sugestoes': disciplinas_do_professor(professor),
        'tamanho_maximo': settings.PROVAS_TAMANHO_MAXIMO,
        'max_arquivos': settings.PROVAS_MAX_ARQUIVOS,
    })


@login_required
def excluir_prova(request, pk):
    prova = get_object_or_404(ProvaAntiga.objects.select_related('professor', 'disciplina'), pk=pk)
    if not prova.pode_excluir(request.user):
        raise PermissionDenied
    if request.method == 'POST':
        professor_pk = prova.professor_id
        prova.delete()  # os arquivos saem do disco pelo sinal post_delete de ArquivoProva
        messages.success(request, 'Prova excluída.')
        return redirect('professor_provas', pk=professor_pk)
    return render(request, 'excluir_prova.html', {'prova': prova, 'professor': prova.professor})


def _servir_arquivo(campo, tipo_conteudo, nome=None):
    try:
        arquivo = campo.open('rb')
    except FileNotFoundError:
        raise Http404
    resposta = FileResponse(arquivo, content_type=tipo_conteudo, filename=nome)  # inline
    resposta['Cache-Control'] = 'public, max-age=86400'
    return resposta


def arquivo_prova(request, pk):
    arquivo = get_object_or_404(ArquivoProva.objects.select_related('prova__disciplina'), pk=pk)
    return _servir_arquivo(arquivo.arquivo, arquivo.tipo_conteudo, arquivo.nome_para_download())


def miniatura_prova(request, pk):
    arquivo = get_object_or_404(ArquivoProva, pk=pk)
    if not arquivo.miniatura:
        raise Http404
    return _servir_arquivo(arquivo.miniatura, 'image/jpeg')


def disciplinas_do_professor(professor):
    """Disciplinas que já têm provas deste professor: viram atalhos no envio e vêm
    primeiro na busca, para a próxima prova cair na mesma disciplina."""
    return Disciplina.objects.filter(provas__professor=professor).distinct().order_by('codigo')


def buscar_disciplinas(request):
    """Sugestões do campo Disciplina: todas as palavras digitadas no código ou nome."""
    termos = normalizar(request.GET.get('q', '')).split()[:6]
    if len(''.join(termos)) < 2:
        return JsonResponse({'resultados': []})

    disciplinas = Disciplina.objects.all()
    for termo in termos:
        disciplinas = disciplinas.filter(busca__contains=termo)

    # Primeiro as do próprio professor, depois as do instituto dele
    prioridade = []
    professor_pk = request.GET.get('professor', '')
    professor = Professor.objects.select_related('instituto').filter(pk=professor_pk).first() if professor_pk.isdigit() else None
    if professor:
        prioridade.append(When(pk__in=disciplinas_do_professor(professor).values('pk'), then=Value(0)))
        if professor.instituto:
            prioridade.append(When(unidade=professor.instituto.nome, then=Value(1)))
    disciplinas = disciplinas.annotate(
        prioridade=Case(*prioridade, default=Value(2), output_field=IntegerField())
    ).order_by('prioridade', 'codigo')[:15]

    return JsonResponse({'resultados': [
        {'codigo': d.codigo, 'nome': d.nome, 'unidade': d.unidade} for d in disciplinas
    ]})