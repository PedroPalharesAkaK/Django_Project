from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.models import User
from .models import Board, Topic, Post

def home(request):
    boards = Board.objects.all()
    return render(request, 'home.html', {'boards': boards})

def board_topics(request, pk):
    board = get_object_or_404(Board, pk=pk)
    return render(request, 'topics.html', {'board': board})

def about(request):
    return render(request, 'about.html')

def new_topic(request, pk):
    # 1. Garante que o quadro existe ou retorna erro 404
    board = get_object_or_404(Board, pk=pk)
    
    # 2. Verifica se o utilizador enviou o formulário (clicou em Post)
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # Por agora, usamos o primeiro utilizador do banco de dados (Hard code temporário)
        user = User.objects.first() 

        # 3. Cria o Tópico (a "pasta" da conversa)
        topic = Topic.objects.create(
            subject=subject,
            board=board,
            starter=user
        )

        # 4. Cria o Post (a mensagem real com o texto)
        post = Post.objects.create(
            message=message,
            topic=topic,
            created_by=user
        )

        # 5. Redireciona de volta para a lista de tópicos do quadro
        return redirect('board_topics', pk=board.pk)

    # 6. Se for um acesso normal (GET), apenas renderiza o template vazio
    return render(request, 'new_topic.html', {'board': board})