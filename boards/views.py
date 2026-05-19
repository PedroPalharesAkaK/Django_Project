from django.shortcuts import render, redirect, get_object_or_404
from .models import Board, Topic, Post
from .forms import NewTopicForm, PostForm
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



class BoardListView(ListView):
    model = Board
    context_object_name = 'boards'
    template_name = 'home.html'


class TopicListView(ListView):
    model = Board  # O Django 6 precisa saber o modelo base para construir a view
    context_object_name = 'topics'
    template_name = 'topics.html'
    paginate_by = 20

    def get_queryset(self):
        # Busca o board ou joga o erro 404
        self.board = get_object_or_404(Board, pk=self.kwargs.get('pk'))
        # Traz os tópicos pertencentes a este board específico
        queryset = self.board.topics.order_by('-last_updated').annotate(replies=Count('posts') - 1)
        return queryset

    def get_context_data(self, **kwargs):
        kwargs['board'] = self.board  # CORREÇÃO: Usa o self.board capturado no get_queryset
        return super().get_context_data(**kwargs)

def about(request):
    return render(request, 'about.html')

# Pode apagar ou comentar a antiga 'def topic_posts' e colar esta no lugar:
from django.shortcuts import get_object_or_404
from django.views.generic import ListView
from django.db.models import F  # Import necessário para incrementar de forma segura
from .models import Topic, Post

class PostListView(ListView):
    model = Post
    context_object_name = 'posts'
    template_name = 'topic_posts.html'
    paginate_by = 2  # Mantido 2 conforme o tutorial para você testar a paginação facilmente

    def get_queryset(self):
        # CORREÇÃO do corte da imagem: Captura o Topic usando a PK do Board ('pk') e a PK do Tópico ('topic_pk')
        self.topic = get_object_or_404(
            Topic, 
            board__pk=self.kwargs.get('pk'), 
            pk=self.kwargs.get('topic_pk')
        )
        # Retorna os posts ordenados por criação
        queryset = self.topic.posts.order_by('created_at')
        return queryset

    def get_context_data(self, **kwargs):
        # CORREÇÃO DJANGO 6 (Segurança): Atualiza as views diretamente no Banco de Dados usando F()
        # Evita bugs se múltiplos usuários acessarem ao mesmo tempo.
        Topic.objects.filter(pk=self.topic.pk).update(views=F('views') + 1)
        
        # Atualiza a instância na memória para o template exibir o número correto imediatamente
        self.topic.refresh_from_db()
        
        kwargs['topic'] = self.topic
        return super().get_context_data(**kwargs)

@login_required
def new_topic(request, pk):
    board = get_object_or_404(Board, pk=pk)
    if request.method == 'POST':
        form = NewTopicForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                topic = form.save(commit=False)
                topic.board = board
                topic.starter = request.user
                topic.save()
                Post.objects.create(
                    message=form.cleaned_data.get('message'),
                    topic=topic,
                    created_by=request.user
                )
            return redirect('topic_posts', pk=pk, topic_pk=topic.pk)
    else:
        form = NewTopicForm()
    
    # ESTA LINHA DEVE FICAR AQUI (ALINHADA COM O PRIMEIRO IF)
    return render(request, 'new_topic.html', {'board': board, 'form': form})


@login_required
def reply_topic(request, pk, topic_pk):
    # Busca o tópico garantindo que ele pertença ao board correto
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    
    if request.method == 'POST':
        form = PostForm(request.POST)
        if form.is_valid():
            post = form.save(commit=False)
            post.topic = topic
            post.created_by = request.user
            post.save()
            
            # Atualiza a data do tópico para que ele suba na listagem
            topic.last_updated = timezone.now()
            topic.save()
            
            return redirect('topic_posts', pk=pk, topic_pk=topic_pk)
    else:
        form = PostForm()
        
    return render(request, 'reply_topic.html', {'topic': topic, 'form': form})

#GCBV


@method_decorator(login_required, name='dispatch')
class PostUpdateView(UpdateView):
    model = Post                         # Mantenha isso para o Django 6 saber que o foco é a tabela Post
    fields = ('message', )
    template_name = 'edit_post.html'
    pk_url_kwarg = 'post_pk'
    context_object_name = 'post'

    def get_queryset(self):
        """
        Filtragem do banco de dados: traz apenas os posts onde o criador 
        seja o usuário logado na requisição (self.request.user).
        """
        queryset = super().get_queryset()
        return queryset.filter(created_by=self.request.user)

    def form_valid(self, form):
        post = form.save(commit=False)
        post.updated_by = self.request.user
        post.updated_at = timezone.now()
        post.save()
        return redirect('topic_posts', pk=post.topic.board.pk, topic_pk=post.topic.pk)