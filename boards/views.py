from django.shortcuts import render, redirect, get_object_or_404
from .models import Board, Topic, Post
from .forms import NewTopicForm
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db import transaction # Adicione este import

def home(request):
    boards = Board.objects.all()
    return render(request, 'home.html', {'boards': boards})

def board_topics(request, pk):
    board = get_object_or_404(Board, pk=pk)
    return render(request, 'topics.html', {'board': board})

def about(request):
    return render(request, 'about.html')

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
            return redirect('board_topics', pk=board.pk)
    else:
        form = NewTopicForm()
    
    # ESTA LINHA DEVE FICAR AQUI (ALINHADA COM O PRIMEIRO IF)
    return render(request, 'new_topic.html', {'board': board, 'form': form})