from django.urls import reverse, resolve
from django.test import TestCase

# IMPORTAÇÕES CORRIGIDAS: Agora chamamos as novas views!
from ..views import new_avaliacao, AvaliacaoListView
# IMPORTAÇÕES CORRIGIDAS: Agora chamamos o modelo Professor!
from ..models import Professor
from django.contrib.auth.models import User

class ProfessorAvaliacoesTests(TestCase):
    def setUp(self):
        # SETUP CORRIGIDO: Em vez de criar um "Board", criamos um "Professor" de teste
        self.professor = Professor.objects.create(
            nome='Professor de Teste', 
            descricao='Departamento de Física'
        )

    def test_professor_avaliacoes_view_success_status_code(self):
        # URL atualizada para 'professor_avaliacoes'
        url = reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_professor_avaliacoes_view_not_found_status_code(self):
        # Passa um ID que sabidamente não existe
        url = reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk + 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)

    def test_professor_avaliacoes_url_resolves_professor_avaliacoes_view(self):
        # Rota atualizada para /professores/
        view = resolve(f'/professores/{self.professor.pk}/')
        # Compara com a nova classe AvaliacaoListView
        self.assertEqual(view.func.view_class, AvaliacaoListView)

    def test_professor_avaliacoes_view_contains_link_back_to_homepage(self):
        professor_avaliacoes_url = reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk})
        response = self.client.get(professor_avaliacoes_url)
        homepage_url = reverse('home')
        self.assertContains(response, f'href="{homepage_url}"')

    def test_professor_avaliacoes_view_contains_navigation_links(self):
        professor_avaliacoes_url = reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk})
        homepage_url = reverse('home')
        new_avaliacao_url = reverse('new_avaliacao', kwargs={'pk': self.professor.pk})

        response = self.client.get(professor_avaliacoes_url)

        # Verifica o link de volta para a Home
        self.assertContains(response, f'href="{homepage_url}"')
        # Verifica o link para criar uma nova avaliação (usará o botão azul se não tiver avaliado)
        self.assertContains(response, f'href="{new_avaliacao_url}"')

    
    