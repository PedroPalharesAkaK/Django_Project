from django.test import TestCase
from ..forms import NewAvaliacaoForm
#testes no limite

class NewAvaliacaoFormTest(TestCase):
    
    def test_form_has_fields(self):
        """
        Garante que o formulário está a carregar todos os 7 campos necessários.
        Se alguém apagar um campo do forms.py por engano, este teste falha.
        """
        form = NewAvaliacaoForm()
        expected = [
            'titulo', 
            'nota_geral', 
            'nota_didatica', 
            'nota_empenho', 
            'nota_relacao', 
            'nota_dificuldade', 
            'texto'
        ]
        self.assertEqual(list(form.fields.keys()), expected)

    def test_valid_form(self):
        """
        Testa o 'Caminho Feliz': Um aluno que preenche tudo corretamente (notas entre 0 e 5).
        """
        data = {
            'titulo': 'Excelente didática',
            'texto': 'As aulas são muito bem estruturadas.',
            'nota_geral': 5,
            'nota_didatica': 4,
            'nota_empenho': 5,
            'nota_relacao': 5,
            'nota_dificuldade': 3
        }
        form = NewAvaliacaoForm(data=data)
        self.assertTrue(form.is_valid())

    def test_invalid_nota_acima_do_limite(self):
        """
        Testa o 'Hacker': Tenta injetar uma nota 6 quando o limite é 5.
        O formulário DEVE ser considerado inválido.
        """
        data = {
            'titulo': 'Professor nota 1000',
            'texto': 'Quero dar nota máxima mais um!',
            'nota_geral': 6,  # <--- INVÁLIDO!
            'nota_didatica': 5,
            'nota_empenho': 5,
            'nota_relacao': 5,
            'nota_dificuldade': 5
        }
        form = NewAvaliacaoForm(data=data)
        
        # O formulário não pode ser válido
        self.assertFalse(form.is_valid())
        # O erro tem de estar especificamente no campo 'nota_geral'
        self.assertTrue('nota_geral' in form.errors)

    def test_invalid_nota_negativa(self):
        """
        Testa valores absurdos: Tenta injetar uma nota negativa.
        """
        data = {
            'titulo': 'Odiei',
            'texto': 'Pior professor.',
            'nota_geral': 1,
            'nota_didatica': -1, # <--- INVÁLIDO!
            'nota_empenho': 1,
            'nota_relacao': 1,
            'nota_dificuldade': 1
        }
        form = NewAvaliacaoForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertTrue('nota_didatica' in form.errors)