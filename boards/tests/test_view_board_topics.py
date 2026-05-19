from django.urls import reverse, resolve
from django.test import TestCase
# CORREÇÃO 1: Removidos os nomes antigos 'home' e 'board_topics' que não existem mais no views.py
from ..views import new_topic, TopicListView
from ..models import Board, Topic, Post
from django.contrib.auth.models import User
from ..forms import NewTopicForm

class BoardTopicsTests(TestCase):
    def setUp(self):
        # CORREÇÃO 2: Guardando o objeto criado em self.board para os métodos usarem dinamicamente
        self.board = Board.objects.create(name='Django', description='Django board.')

    def test_board_topics_view_success_status_code(self):
        url = reverse('board_topics', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_board_topics_view_not_found_status_code(self):
        # Passa um ID que sabidamente não existe (somando 1 ao ID atual)
        url = reverse('board_topics', kwargs={'pk': self.board.pk + 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_board_topics_url_resolves_board_topics_view(self):
        # Agora o self.board.pk vai funcionar perfeitamente!
        view = resolve(f'/boards/{self.board.pk}/')
        # CORREÇÃO DJANGO 6: Compara com a classe usando .view_class
        self.assertEqual(view.func.view_class, TopicListView)

    def test_board_topics_view_contains_link_back_to_homepage(self):
        board_topics_url = reverse('board_topics', kwargs={'pk': self.board.pk})
        response = self.client.get(board_topics_url)
        homepage_url = reverse('home')
        self.assertContains(response, f'href="{homepage_url}"')

    def test_board_topics_view_contains_navigation_links(self):
        board_topics_url = reverse('board_topics', kwargs={'pk': self.board.pk})
        homepage_url = reverse('home')
        new_topic_url = reverse('new_topic', kwargs={'pk': self.board.pk})

        response = self.client.get(board_topics_url)

        # Verifica o link de volta para a Home
        self.assertContains(response, f'href="{homepage_url}"')
        # Verifica o link para criar um novo tópico
        self.assertContains(response, f'href="{new_topic_url}"')


    
    