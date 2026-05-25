from django.test import TestCase
from django.contrib.auth.models import User
from ..models import Professor, Avaliacao

class ProfessorModelTests(TestCase):
    def setUp(self):
        # Criação do cenário: Um docente de Física e dois alunos
        self.professor = Professor.objects.create(nome='Docente de Física', descricao='IFUSP')
        self.aluno1 = User.objects.create_user(username='aluno1', password='123')
        self.aluno2 = User.objects.create_user(username='aluno2', password='123')

    def test_professor_sem_avaliacoes_retorna_zero(self):
        """
        Garante que um professor sem reviews devolve 0 e não causa erros de divisão por zero (DivisionByZero).
        """
        self.assertEqual(self.professor.get_media_geral(), 0)
        self.assertEqual(self.professor.get_percent_geral(), 0)

    def test_professor_com_avaliacoes_calcula_media_correta(self):
        """
        Simula duas avaliações para verificar se a matemática do Django está correta.
        Aluno 1 dá nota 5 em tudo. Aluno 2 dá nota 3 em tudo.
        A média esperada é 4.0, e a percentagem da barra deve ser 80% (pois 4 de 5 é 80%).
        """
        Avaliacao.objects.create(
            titulo='Review 1', professor=self.professor, starter=self.aluno1,
            nota_geral=5, nota_didatica=5, nota_empenho=5, nota_relacao=5, nota_dificuldade=5
        )
        
        Avaliacao.objects.create(
            titulo='Review 2', professor=self.professor, starter=self.aluno2,
            nota_geral=3, nota_didatica=3, nota_empenho=3, nota_relacao=3, nota_dificuldade=3
        )
        
        # Testamos se o cálculo da média decimal está a funcionar
        self.assertEqual(self.professor.get_media_geral(), 4.0)
        
        # Testamos se a conversão para número inteiro da barra do Bootstrap está a funcionar
        self.assertEqual(self.professor.get_percent_geral(), 80)
        self.assertEqual(self.professor.get_percent_didatica(), 80)
        self.assertEqual(self.professor.get_percent_dificuldade(), 80)