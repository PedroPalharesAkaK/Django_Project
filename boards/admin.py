
from django.contrib import admin
from .models import Professor, Avaliacao, Comentario
from .models import Universidade

# Registar as novas tabelas para aparecerem no painel /admin/
admin.site.register(Professor)
admin.site.register(Avaliacao)
admin.site.register(Comentario)
admin.site.register(Universidade)