
from django.contrib import admin
from .models import Universidade, Instituto, Professor, Avaliacao, Comentario, Contato
# Registar as novas tabelas para aparecerem no painel /admin/
admin.site.register(Professor)
admin.site.register(Avaliacao)
admin.site.register(Comentario)
admin.site.register(Universidade)
admin.site.register(Instituto)


from .models import Contato

# Esta linha "regista" a tabela e aplica as configurações abaixo
@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    # Quais colunas você quer ver na lista principal
    list_display = ('nome', 'email', 'criado_em')
    
    # Adiciona uma barra de pesquisa para achar mensagens rápido
    search_fields = ('nome', 'email', 'mensagem')
    
    # Filtro lateral por data
    list_filter = ('criado_em',)
    
    # Proteção: Impede que o admin edite a data em que a mensagem foi enviada
    readonly_fields = ('criado_em',)


from .models import Disciplina, ArquivoProva, ProvaAntiga


@admin.register(Disciplina)
class DisciplinaAdmin(admin.ModelAdmin):
    list_display = ('codigo', 'nome', 'unidade')
    search_fields = ('codigo', 'nome')
    list_filter = ('unidade',)


class ArquivoProvaInline(admin.TabularInline):
    model = ArquivoProva
    extra = 0
    fields = ('ordem', 'tipo_conteudo', 'tamanho', 'arquivo')
    readonly_fields = ('tipo_conteudo', 'tamanho', 'arquivo')
    can_delete = True


@admin.register(ProvaAntiga)
class ProvaAntigaAdmin(admin.ModelAdmin):
    list_display = ('disciplina', 'semestre', 'tipo', 'professor', 'enviado_por', 'criado_em')
    list_filter = ('tipo', 'semestre')
    search_fields = ('disciplina__codigo', 'disciplina__nome', 'professor__nome', 'enviado_por__username')
    # Os campos de busca evitam carregar milhares de opções nos selects
    raw_id_fields = ('professor', 'disciplina', 'enviado_por')
    readonly_fields = ('criado_em',)
    inlines = [ArquivoProvaInline]