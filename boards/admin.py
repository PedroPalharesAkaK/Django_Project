
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