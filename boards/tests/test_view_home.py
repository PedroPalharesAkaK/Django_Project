from django.urls import reverse, resolve
from django.test import TestCase

# 1. IMPORTAÇÕES ATUALIZADAS: Chamando a nova View da página inicial
from ..views import ProfessorListView
# 2. IMPORTAÇÕES ATUALIZADAS: Chamando o novo modelo Professor
from ..models import Professor

class HomeTests(TestCase):
    def setUp(self):
        # 3. SETUP CORRIGIDO: Cria um professor de teste para garantir que a tabela da Home não esteja vazia
        self.professor = Professor.objects.create(
            nome='Professor de Teste', 
            descricao='Departamento de Física'
        )
        url = reverse('home')
        self.response = self.client.get(url)

    def test_home_view_status_code(self):
        # Verifica se a página carrega corretamente (Status 200)
        self.assertEqual(self.response.status_code, 200)

    def test_home_url_resolves_home_view(self):
        # 4. RESOLVE CORRIGIDO: Verifica se a URL '/' encaminha para a nova ProfessorListView
        view = resolve('/')
        self.assertEqual(view.func.view_class, ProfessorListView)

    def test_home_view_contains_link_to_topics_page(self):
        # 5. ROTA E LINK CORRIGIDOS: Verifica se o link do nome do professor aponta para as suas avaliações
        professor_avaliacoes_url = reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk})
        self.assertContains(self.response, f'href="{professor_avaliacoes_url}"')
    
    
    