from django.urls import reverse, resolve
from django.test import TestCase
from ..views import home, board_topics, new_topic
from ..models import Board, Topic, Post
from django.contrib.auth.models import User
from ..forms import NewTopicForm

class BoardTopicsTests(TestCase):
    def setUp(self):
        # Cria um board para os testes
        Board.objects.create(name='Django', description='Django board.')

    def test_board_topics_view_success_status_code(self):
        url = reverse('board_topics', kwargs={'pk': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_board_topics_view_not_found_status_code(self):
        url = reverse('board_topics', kwargs={'pk': 99})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_board_topics_url_resolves_board_topics_view(self):
        view = resolve('/boards/1/')
        self.assertEqual(view.func, board_topics)

    def test_board_topics_view_contains_link_back_to_homepage(self):
        board_topics_url = reverse('board_topics', kwargs={'pk': 1})
        response = self.client.get(board_topics_url)
        homepage_url = reverse('home')
        # Usando f-string em vez de .format()
        self.assertContains(response, f'href="{homepage_url}"')
    def test_board_topics_view_contains_navigation_links(self):
        board_topics_url = reverse('board_topics', kwargs={'pk': 1})
        homepage_url = reverse('home')
        new_topic_url = reverse('new_topic', kwargs={'pk': 1})

        response = self.client.get(board_topics_url)

     # Verifica o link de volta para a Home
        self.assertContains(response, f'href="{homepage_url}"')
    # Verifica o link para criar um novo tópico
        self.assertContains(response, f'href="{new_topic_url}"')


    
    