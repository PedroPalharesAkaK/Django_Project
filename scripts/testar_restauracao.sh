#!/usr/bin/env bash
# Prova que o backup volta: baixa do Azure a cópia mais recente do banco,
# restaura num banco temporário (teste_restauracao) dentro do mesmo Postgres,
# compara com o banco do site e apaga o temporário. Não altera o forum_db.
set -euo pipefail

PROJETO="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO="${BACKUP_DESTINO:-backup:backups}"
TEMP="$(mktemp -d)"
cd "$PROJETO"

no_postgres() { docker compose exec -T db "$@"; }
contar() { no_postgres psql -U forum_user -d "$1" -tAc "select count(*) from $2"; }
limpar() {
    no_postgres dropdb -U forum_user --if-exists teste_restauracao || true
    rm -rf "$TEMP"
}
trap limpar EXIT

ULTIMO="$(rclone lsf "$DESTINO/banco/" | sort | tail -n 1)"
if [ -z "$ULTIMO" ]; then
    echo "Nenhuma cópia do banco no Azure." >&2
    exit 1
fi
echo "Restaurando $ULTIMO num banco temporário..."
rclone copy "$DESTINO/banco/$ULTIMO" "$TEMP/"

no_postgres dropdb -U forum_user --if-exists teste_restauracao
no_postgres createdb -U forum_user teste_restauracao
no_postgres pg_restore -U forum_user -d teste_restauracao --no-owner --no-privileges < "$TEMP/$ULTIMO"

echo
printf '%-22s %8s %8s\n' 'tabela' 'site' 'backup'
for tabela in auth_user boards_professor boards_avaliacao boards_comentario boards_disciplina boards_provaantiga boards_arquivoprova; do
    printf '%-22s %8s %8s\n' "$tabela" "$(contar forum_db "$tabela")" "$(contar teste_restauracao "$tabela")"
done

echo
echo "Arquivos de provas: $(find media -type f | wc -l) no servidor, $(rclone lsf -R --files-only "$DESTINO/media/" | wc -l) no Azure"
echo "(diferenças pequenas são normais se o site foi usado depois do backup;"
echo " o Azure pode ter mais arquivos, porque o backup nunca apaga nada lá)"
