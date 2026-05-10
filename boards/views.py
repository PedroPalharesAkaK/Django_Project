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
    board = get_object_or_404(Board, pk=pk)
    user = User.objects.first() 
    
    if request.method == 'POST':
        subject = request.POST.get('subject')
        message = request.POST.get('message')

        # ADICIONE ESTA VALIDAÇÃO:
        if subject and message:  # Só cria se ambos tiverem conteúdo
            topic = Topic.objects.create(
                subject=subject,
                board=board,
                starter=user
            )
            post = Post.objects.create(
                message=message,
                topic=topic,
                created_by=user
            )
            return redirect('board_topics', pk=board.pk)
        
        # Se os dados forem inválidos, o código continua para baixo
        # e renderiza o form novamente (Status 200), satisfazendo o teste.

    return render(request, 'new_topic.html', {'board': board})