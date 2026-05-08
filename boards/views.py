from django.shortcuts import render
from .models import Board

def home(request):
    boards = Board.objects.all()
    return render(request, 'home.html', {'boards': boards})

def board_topics(request, pk):
    # Por enquanto, apenas para o site não quebrar:
    return render(request, 'topics.html', {'pk': pk})

def about(request):
    return render(request, 'about.html')