from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from .models import Professor, Avaliacao, Comentario
from .forms import NewAvaliacaoForm, ComentarioForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction # Adicione este import
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.generic import UpdateView
from django.db.models import Count
from django.views.generic import ListView
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger 
from django.db.models import F



class ProfessorListView(ListView):
    model = Professor
    context_object_name = 'professors'
    template_name = 'home.html'


class AvaliacaoListView(ListView):
    model = Professor
    context_object_name = 'avaliacoes'
    template_name = 'avaliacoes.html'
    paginate_by = 20

    def get_queryset(self):
        self.professor = get_object_or_404(Professor, pk=self.kwargs.get('pk'))
        queryset = self.professor.avaliacoes.order_by('-last_updated').annotate(replies=Count('comentarios') - 1)
        return queryset

    def get_context_data(self, **kwargs):
        kwargs['professor'] = self.professor
        
        # --- A NOSSA NOVA MÁGICA DE INVESTIGAÇÃO ---
        # Se o utilizador estiver logado, verifica se já existe uma avaliação dele para este professor
        if self.request.user.is_authenticated:
            kwargs['usuario_ja_avaliou'] = Avaliacao.objects.filter(
                professor=self.professor, 
                starter=self.request.user
            ).exists()
        else:
            kwargs['usuario_ja_avaliou'] = False
            
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

@login_required
def new_avaliacao(request, pk):
    professor = get_object_or_404(Professor, pk=pk)
    
    # --- O SEGURANÇA DA PORTA (BACKEND) ---
    # Verifica na base de dados se este aluno já avaliou este professor
    ja_avaliou = Avaliacao.objects.filter(professor=professor, starter=request.user).exists()
    
    if ja_avaliou:
        # Se for um espertinho a tentar forçar o URL, é redirecionado imediatamente!
        return redirect('professor_avaliacoes', pk=professor.pk)
    # ---------------------------------------

    if request.method == 'POST':
        form = NewAvaliacaoForm(request.POST)
        if form.is_valid():
            avaliacao = form.save(commit=False)
            avaliacao.professor = professor
            avaliacao.starter = request.user
            avaliacao.save()
            
            Comentario.objects.create(
                texto=form.cleaned_data.get('texto'), 
                avaliacao=avaliacao,
                created_by=request.user
            )
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

            # --- A NOVA MÁGICA ENTRA AQUI ---
            # 1. Gera a string da URL base
            avaliacao_url = reverse('avaliacao_comentarios', kwargs={'pk': pk, 'avaliacao_pk': avaliacao_pk})
            
            # 2. Monta a URL completa com a página final e a âncora do comentario (usando f-string)
            avaliacao_comentario_url = f"{avaliacao_url}?page={avaliacao.get_page_count()}#{comentario.pk}"
            
            # 3. Redireciona o utilizador
            return redirect(avaliacao_comentario_url)
    else:
        form = ComentarioForm()
    return render(request, 'reply_avaliacao.html', {'avaliacao': avaliacao, 'form': form})
#GCBV


@method_decorator(login_required, name='dispatch')
class ComentarioUpdateView(UpdateView):
    model = Comentario                         
    fields = ('texto', )  # Correção: 'message' agora é 'texto'
    template_name = 'edit_comentario.html'
    pk_url_kwarg = 'comentario_pk'
    context_object_name = 'comentario'

    def get_queryset(self):
        """
        Filtragem do banco de dados: traz apenas os comentarios onde o criador 
        seja o usuário logado na requisição (self.request.user).
        """
        queryset = super().get_queryset()
        return queryset.filter(created_by=self.request.user)

    def form_valid(self, form):
        comentario = form.save(commit=False)
        comentario.updated_by = self.request.user
        comentario.updated_at = timezone.now()
        comentario.save()
        # O caminho de volta está perfeito, usando os nomes corretos!
        return redirect('avaliacao_comentarios', pk=comentario.avaliacao.professor.pk, avaliacao_pk=comentario.avaliacao.pk)
    
# Adicione esta função para evitar erros com a rota 'about' do seu urls.py
def about(request):
    return render(request, 'about.html')