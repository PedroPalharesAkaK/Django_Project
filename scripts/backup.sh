#!/usr/bin/env bash
# Backup diário do avaliaprofessor.app no Azure Blob Storage (contêiner "backups").
#
#   banco/   cópia do Postgres (pg_dump -Fc, já comprimido), uma por execução;
#            o próprio Azure apaga as com mais de 30 dias (regra de ciclo de vida)
#   media/   arquivos das provas: só envia os novos e nunca apaga nada lá
#   config/  /etc/nginx, que fica fora do git (limite de upload etc.)
#
# A chave do rclone (SAS) pode ler, criar, escrever e listar, mas não apagar; com o
# versionamento ligado no Azure, sobrescrever um arquivo guarda a versão anterior.
# Assim um erro ou uma invasão aqui no servidor não destrói o que já foi enviado.
# (O rclone precisa de Write para enviar; o script mesmo nunca sobrescreve nada.)
#
# Roda pelo cron do servidor. Instalação e restauração: docs/backup.md
set -euo pipefail

PROJETO="$(cd "$(dirname "$0")/.." && pwd)"
DESTINO="${BACKUP_DESTINO:-backup:backups}"

# Opcional: HEALTHCHECK_URL=https://hc-ping.com/... (avisa por e-mail se o backup parar)
CONFIG="$HOME/.config/backup-avaliaprofessor.env"
if [ -f "$CONFIG" ]; then
    . "$CONFIG"
fi

TEMP="$(mktemp -d)"
trap 'rm -rf "$TEMP"' EXIT
AGORA="$(date -u +%Y-%m-%d_%H%M%S)"
cd "$PROJETO"

# 1. Banco. O -T evita que o docker altere os bytes do arquivo.
DUMP="$TEMP/banco-$AGORA.dump"
docker compose exec -T db pg_dump -U forum_user -Fc forum_db > "$DUMP"
if [ "$(head -c 5 "$DUMP")" != "PGDMP" ]; then
    echo "$(date '+%F %T') ERRO: o pg_dump gerou um arquivo inválido" >&2
    exit 1
fi
rclone copy "$DUMP" "$DESTINO/banco/"

# 2. Provas: só o que ainda não está no Azure
rclone copy --ignore-existing --transfers 2 media "$DESTINO/media/"

# 3. Configuração do nginx
tar -czf "$TEMP/config-$AGORA.tar.gz" -C / etc/nginx
rclone copy "$TEMP/config-$AGORA.tar.gz" "$DESTINO/config/"

# 4. Avisa o healthchecks.io que deu certo; se o aviso não chegar, ele manda e-mail
if [ -n "${HEALTHCHECK_URL:-}" ]; then
    curl -fsS -m 10 --retry 3 "$HEALTHCHECK_URL" > /dev/null
fi

echo "$(date '+%F %T') backup ok (banco com $(du -h "$DUMP" | cut -f1))"
