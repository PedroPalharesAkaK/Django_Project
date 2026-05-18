from django.shortcuts import render, redirect, get_object_or_404
from .models import Board, Topic, Post
from .forms import NewTopicForm, PostForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction # Adicione este import
from django.utils import timezone
from django.views.generic import UpdateView
from django.db.models import Count
from django.db.models import F
def home(request):
    boards = Board.objects.all()
    return render(request, 'home.html', {'boards': boards})

def board_topics(request, pk):
    board = get_object_or_404(Board, pk=pk)
    topics = board.topics.order_by('-last_updated').annotate(replies=Count('posts') - 1)
    return render(request, 'topics.html', {'board': board, 'topics': topics})

def about(request):
    return render(request, 'about.html')

def topic_posts(request, pk, topic_pk):
    # 1. Faz a primeira e única consulta ao banco de dados
    topic = get_object_or_404(Topic, board__pk=pk, pk=topic_pk)
    
    # 2. Soma +1 diretamente na memória do Python (Super rápido!)
    topic.views += 1
    
    # 3. Guarda o novo valor no banco de dados
    topic.save()
    
    # Como o valor já está atualizado na memória do Python, 
    # o template vai receber o número correto sem precisar de reconsultar o banco.
    return render(request, 'topic_posts.html', {'topic': topic})

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
class PostUpdateView(UpdateView):
    model = Post
    fields = ('message', )
    template_name = 'edit_post.html'
    pk_url_kwarg = 'post_pk'
    context_object_name = 'post'

    def form_valid(self, form):
        post = form.save(commit=False)
        post.updated_by = self.request.user
        post.updated_at = timezone.now()
        post.save()
        return redirect('topic_posts', pk=post.topic.board.pk, topic_pk=post.topic.pk)