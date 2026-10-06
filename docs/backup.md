# Backup do avaliaprofessor.app

Todo dia o servidor envia uma cópia do site para o Azure Blob Storage
(conta de armazenamento na assinatura "Azure for Students", contêiner `backups`):

| Pasta no Azure | O que é | Quanto tempo fica |
|---|---|---|
| `banco/` | cópia completa do Postgres (`pg_dump`), uma por dia | 30 dias (o Azure apaga as mais velhas) |
| `media/` | arquivos das provas; só os novos são enviados | para sempre; o backup nunca apaga nada |
| `config/` | `/etc/nginx` (limite de upload), que não está no git | 30 dias |

O código está no GitHub e não entra no backup.

A chave que fica no servidor (uma URL SAS) permite **ler, criar, escrever e listar**,
mas não apagar. Com o versionamento ligado, sobrescrever um arquivo guarda a versão
anterior, e a chave também não apaga versões. Nem um erro nem uma invasão no servidor
conseguem destruir o que já está no Azure. (O rclone precisa de *Write* para enviar
arquivos: só com *Create* ele recebe `AuthorizationPermissionMismatch`.)

A conta de armazenamento `backupavaliaprofessor` foi criada em Mexico Central, a mesma
região da VM.

Scripts: `scripts/backup.sh` (roda no cron) e `scripts/testar_restauracao.sh`.

---

## Instalação (uma vez)

### 1. No portal do Azure

1. **Criar a conta de armazenamento**: *Storage accounts* → *Create*.
   - Resource group: `rg-forum-avaliacoes`
   - Nome: `backupavaliaprofessor` (só letras minúsculas e números; se estiver em uso, acrescente números)
   - Region: de preferência **diferente** da VM (ex.: *Brazil South*), para a cópia ficar longe
     do servidor. Na mesma região também funciona; veja o campo de IP no passo 5.
   - Primary service: *Azure Blob Storage or Azure Data Lake Storage Gen 2*
   - Performance: *Standard*; Redundancy: *Locally-redundant storage (LRS)*
   - Nas outras abas, mantenha o padrão (acesso anônimo desligado, soft delete ligado) → *Review + create* → *Create*.
2. **Ligar o versionamento**: *Data management* → *Data protection* → marque
   *Enable versioning for blobs* → *Save*.
3. **Criar o contêiner**: na conta criada, *Data storage* → *Containers* → *+ Container*,
   nome `backups`, acesso anônimo *Private*.
4. **Regra de 30 dias**: *Data management* → *Lifecycle management* → *Add a rule*.
   - Nome `apagar-copias-antigas`; escopo *Limit blobs with filters*; tipo *Block blobs*;
     subtipos *Base blobs* e *Versions*.
   - Base blobs: *Last modified* há mais de `30` dias → *Delete the blob* (os arquivos nunca são
     modificados, então isso é o mesmo que a data de envio).
   - Versions: *Created* há mais de `30` dias → *Delete the blob version*. Com o versionamento
     ligado, um arquivo apagado vira uma versão antiga; sem esta parte ele nunca sairia de vez.
   - Filtros (prefixos): `backups/banco/` e `backups/config/`. **Não** inclua `backups/media/`.

   A regra existente (criada em 06/10/2026), vista em *Code View*:
   ```json
   {"rules": [{"enabled": true, "name": "apagar-copias-antigas", "type": "Lifecycle",
     "definition": {
       "actions": {"version": {"delete": {"daysAfterCreationGreaterThan": 30}},
                   "baseBlob": {"delete": {"daysAfterModificationGreaterThan": 30}}},
       "filters": {"blobTypes": ["blockBlob"],
                   "prefixMatch": ["backups/banco/", "backups/config/"]}}}]}
   ```
5. **Gerar a chave do servidor**: *Containers* → `backups` → *Shared access tokens*.
   - Signing method *Account key*, Signing key *Key 1*
   - Permissions: marque só **Read**, **Create**, **Write** e **List** (nunca *Delete*)
   - Expiry: daqui a 1 ano (anote a data: a chave para de funcionar nesse dia)
   - Allowed IP addresses: **vazio** se a conta está na mesma região da VM (lá dentro o Azure
     usa endereços internos e o IP público não seria reconhecido). Em outra região, use o IP
     do servidor (`68.155.147.141`) para a chave só funcionar a partir dele.
   - Allowed protocols: *HTTPS only*
   - *Generate SAS token and URL* → copie a **Blob SAS URL**.
   Ela é uma senha: não mande para ninguém nem guarde no projeto.

### 2. No servidor (SSH)

```bash
sudo apt update && sudo apt install -y rclone
```

Configure a chave. Comece a linha com um **espaço** para ela não ficar no histórico
do terminal, e cole a Blob SAS URL entre as aspas simples. O `> /dev/null` é importante:
sem ele o rclone mostra a configuração, com a chave inteira, na tela.

```bash
 rclone config create backup azureblob sas_url 'COLE_AQUI_A_BLOB_SAS_URL' > /dev/null
```

Teste a conexão (não deve mostrar erro; o contêiner ainda está vazio):

```bash
rclone lsf backup:backups
```

Se aparecer `403` ou `AuthorizationSourceIPMismatch`, a restrição de IP não bateu: gere a
chave de novo (passo 1.5) deixando *Allowed IP addresses* vazio e repita o `rclone config create`.

Primeiro backup, na mão (a primeira vez envia todas as provas e demora mais):

```bash
bash ~/Django_Project/scripts/backup.sh
```

Teste de restauração (restaura num banco temporário e compara com o do site):

```bash
bash ~/Django_Project/scripts/testar_restauracao.sh
```

Agendar para todo dia às 4h30 no horário do servidor (UTC, 1h30 em Brasília):

```bash
mkdir -p ~/backups && (crontab -l 2>/dev/null | grep -v scripts/backup.sh; echo '30 4 * * * bash $HOME/Django_Project/scripts/backup.sh >> $HOME/backups/backup.log 2>&1') | crontab -
```

### 3. Aviso por e-mail se o backup parar (opcional, recomendado)

Crie uma conta gratuita em https://healthchecks.io, crie um *check* com período de
1 dia e tolerância de 2 horas, e copie a URL de ping. No servidor:

```bash
mkdir -p ~/.config && echo 'HEALTHCHECK_URL=COLE_AQUI_A_URL_DE_PING' > ~/.config/backup-avaliaprofessor.env
```

Se um dia o backup não rodar ou der erro, o healthchecks.io manda um e-mail.

---

## No dia a dia

- Ver se os backups estão rodando: `tail ~/backups/backup.log` (uma linha "backup ok" por dia).
- Ver o que está no Azure: `rclone lsf backup:backups/banco/`.
- Repetir o teste de restauração de vez em quando (a cada poucos meses).
- **Renovar a chave antes de ela vencer**: gere uma nova SAS (passo 1.5) e troque no servidor:
  ` rclone config update backup sas_url 'NOVA_URL' > /dev/null` (com o espaço no início).
- Se a chave vazar: no portal, *Security + networking* → *Access keys* → *Rotate key* na
  Key 1. Isso invalida a chave antiga; depois gere uma nova.

---

## Restaurar (emergência ou servidor novo)

Pré-requisitos no servidor novo: Docker, o projeto clonado do GitHub em `~/Django_Project`,
o rclone configurado com uma SAS nova (passos 1.4 e 2, com o IP do servidor novo).

1. Baixar as provas:
   ```bash
   rclone copy backup:backups/media ~/Django_Project/media
   ```
2. Baixar a cópia mais recente do banco:
   ```bash
   rclone lsf backup:backups/banco/ | sort | tail -n 1
   ```
   ```bash
   rclone copy backup:backups/banco/NOME_DO_ARQUIVO.dump ~/
   ```
3. Subir só o banco, vazio, e restaurar nele:
   ```bash
   cd ~/Django_Project && docker compose up -d db
   ```
   ```bash
   docker compose exec -T db pg_restore -U forum_user -d forum_db --no-owner --clean --if-exists < ~/NOME_DO_ARQUIVO.dump
   ```
4. Subir o site e conferir:
   ```bash
   docker compose up -d --build && docker compose exec web python manage.py collectstatic --noinput && docker compose restart web
   ```
5. nginx: a configuração antiga está em `backup:backups/config/` (um `.tar.gz` de `/etc/nginx`);
   baixe a mais recente e compare antes de copiar arquivos para o `/etc/nginx` novo.

Também é possível baixar qualquer arquivo pelo portal do Azure (*Containers* → `backups`),
entrando com a sua conta, sem precisar da SAS.
