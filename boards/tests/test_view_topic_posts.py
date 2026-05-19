from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import resolve, reverse

from ..models import Board, Post, Topic
# CORREÇÃO 1: Garanta que estás a importar a view correta (seja ela TopicPostsListView ou equivalente)
# Substitua pelo nome real da tua view de listagem de posts, caso seja diferente:
from ..views import TopicListView 

class TopicPostsTests(TestCase):
    def setUp(self):
        # CORREÇÃO 2: Guardar o board, o tópico e o usuário em variáveis 'self.' 
        # para que os testes usem IDs dinâmicos reais e nunca IDs estáticos (como 1)
        self.board = Board.objects.create(name='Django', description='Django board.')
        self.user = User.objects.create_user(username='john', email='john@doe.com', password='123')
        self.topic = Topic.objects.create(subject='Hello, world', board=self.board, starter=self.user)
        self.post = Post.objects.create(message='Lorem ipsum dolor sit amet', topic=self.topic, created_by=self.user)
        
        # Gera a URL dinamicamente usando as PKs reais do banco de testes
        self.url = reverse('topic_posts', kwargs={'pk': self.board.pk, 'topic_pk': self.topic.pk})
        self.response = self.client.get(self.url)

    def test_status_code(self):
        self.assertEqual(self.response.status_code, 200)

    def test_view_class(self):
        view = resolve(f'/boards/{self.board.pk}/topics/{self.topic.pk}/')
        # Se ainda for uma função, usamos views.topic_posts diretamente:
        from .. import views
        self.assertEqual(view.func, views.topic_posts)

    def test_contains_navigation_links(self):
        # CORREÇÃO 4: Gerar os links de navegação usando as PKs dinâmicas do setUp
        homepage_url = reverse('home')
        board_topics_url = reverse('board_topics', kwargs={'pk': self.board.pk})
        
        # Verifica se o HTML contém os links corretos de volta para a Home e para o Board
        self.assertContains(self.response, f'href="{homepage_url}"')
        self.assertContains(self.response, f'href="{board_topics_url}"')