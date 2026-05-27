from django.test import TestCase
from django.urls import reverse
from boards.models import Professor

class ProfessorVisualizacoesTests(TestCase):
    def setUp(self):
        # Cria um professor no banco de dados isolado de testes
        self.professor = Professor.objects.create(
            nome='Professor Albert Einstein',
            descricao='Departamento de Física',
            visualizacoes=0
        )
        # Prepara a URL da página do professor que queremos testar
        self.url = reverse('professor_avaliacoes', kwargs={'pk': self.professor.pk})

    def test_visualizacao_incrementa_na_primeira_visita(self):
        """Garante que a primeira visita de um aluno soma +1 ao contador."""
        # 1. Fazemos uma requisição GET (como se um aluno abrisse a página)
        self.client.get(self.url)
        
        # 2. Puxamos os dados atualizados do banco de dados
        self.professor.refresh_from_db()
        
        # 3. Verificamos se a visualização subiu de 0 para 1
        self.assertEqual(self.professor.visualizacoes, 1)

    def test_visualizacao_bloqueia_f5_seguidos(self):
        """Garante que o aluno não consegue inflar os números apertando F5."""
        # Visita 1 (O contador deve ir para 1 e o Django deve marcar a sessão)
        self.client.get(self.url)
        
        # Visita 2 (O famoso recarregar a página)
        self.client.get(self.url)
        
        # Visita 3 (Tentando fazer spam)
        self.client.get(self.url)
        
        self.professor.refresh_from_db()
        
        # O teste SÓ PASSA se o número continuar sendo estritamente 1
        self.assertEqual(self.professor.visualizacoes, 1)