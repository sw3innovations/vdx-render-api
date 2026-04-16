# VDX Glass Engine — Guia de Operações

## Backup do Banco de Dados

### Agendamento

O backup é executado diariamente às 3h via cron/systemd.

**macOS (dev):** crontab
```
0 3 * * * cd /path/to/vdx-render-api && BACKUP_DIR=$HOME/backups/vdx bash tools/backup_db.sh >> $HOME/backups/vdx/backup.log 2>&1
```

Verificar se está ativo:
```bash
crontab -l | grep backup_db
```

**Linux/VPS (produção):** systemd timer
```bash
sudo systemctl list-timers | grep vdx-backup
```

### Arquivos gerados

```
$HOME/backups/vdx/
  constitution_20260416_030001.db   # snapshot atômico via VACUUM INTO
  backup.log                        # log de execuções
```

- Retenção: 7 dias (configurável via `KEEP_DAYS=N` antes do script)
- Tamanho típico: ~270–300KB

### Como verificar integridade

```bash
LATEST=$(ls -t ~/backups/vdx/constitution_*.db | head -1)
sqlite3 "$LATEST" "PRAGMA integrity_check;"
sqlite3 "$LATEST" "SELECT COUNT(*) FROM ferragens;"  # esperado: 158
```

### Como restaurar

```bash
# 1. Parar a aplicação
pkill -f "uvicorn app.main"

# 2. Fazer backup do banco atual (por precaução)
cp data/constitution.db data/constitution.db.pre-restore

# 3. Restaurar o snapshot desejado
SNAPSHOT=~/backups/vdx/constitution_YYYYMMDD_HHMMSS.db
cp "$SNAPSHOT" data/constitution.db

# 4. Verificar integridade
sqlite3 data/constitution.db "PRAGMA integrity_check;"

# 5. Reiniciar a aplicação
uvicorn app.main:app --host 0.0.0.0 --port 8000 &
```

### Executar manualmente

```bash
# Backup imediato
bash tools/backup_db.sh

# Dry-run (mostra o que faria, sem gravar)
bash tools/backup_db.sh --dry-run

# Backup em diretório alternativo
BACKUP_DIR=/tmp/backup_teste bash tools/backup_db.sh
```

---

## Variáveis de Ambiente

| Variável | Padrão | Descrição |
|---|---|---|
| `VDX_API_MASTER_KEY` | `""` | Chave de API (vazio = modo dev, sem auth) |
| `ANTHROPIC_API_KEY` | `""` | Chave da API Anthropic (Claude) |
| `DB_PATH` | `data/constitution.db` | Caminho do banco SQLite |
| `MAX_BODY_SIZE_KB` | `100` | Limite de tamanho do request body |
| `CORS_ORIGINS` | `*` | Origins permitidas (separadas por vírgula) |
| `LOG_DIR` | `logs/` | Diretório dos logs de aplicação |
| `BACKUP_DIR` | `$HOME/backups/vdx` | Destino dos backups (script) |
| `KEEP_DAYS` | `7` | Retenção de backups em dias |
| `VDX_VIEW_TOKEN_SECRET` | `""` | Segredo para JWTs do viewer (**obrigatório em produção**) |
| `VDX_VIEW_TOKEN_TTL_SECONDS` | `3600` | TTL padrão do view token (segundos) |
| `VDX_VIEW_TOKEN_MAX_TTL_SECONDS` | `86400` | TTL máximo solicitável pelo cliente |

---

## View Tokens (Viewer 3D Compartilhável)

O viewer 3D suporta dois modos de autenticação:

| Modo | Como usar | Caso de uso |
|---|---|---|
| **Header** | `X-VDX-Key: <key>` no fetch | SDK, integração server-side |
| **Token** | `?t=<jwt>` na URL | Browser, WhatsApp, iframe, e-mail |

### Emitir um view token

```bash
# Gera token com 1h de validade (padrão)
curl -s -X POST http://localhost:8000/api/v1/3d/viewer/token \
  -H "X-VDX-Key: $VDX_API_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tipologia":"porta_pivotante_simples","largura":900,"altura":2100}' \
  | jq '{url, expires_in}'

# Com TTL customizado (24h = 86400s)
curl -s -X POST http://localhost:8000/api/v1/3d/viewer/token \
  -H "X-VDX-Key: $VDX_API_MASTER_KEY" \
  -H "Content-Type: application/json" \
  -d '{"tipologia":"janela_3_folhas","largura":1500,"altura":1200,"ttl_seconds":86400}'
```

A `url` retornada pode ser aberta diretamente no browser ou enviada por WhatsApp.

### SDK TypeScript

```ts
const client = new VDXClient('my-api-key')

// Gera URL compartilhável (chama POST /token internamente)
const { url, expires_in } = await client.createShareableUrl(
  'porta_pivotante_simples', 900, 2100,
  { cor_vidro: 'verde', ttl_seconds: 7200 }
)
console.log(`Link válido por ${expires_in}s: ${url}`)
```

### Configuração de produção

Gere um segredo forte e configure no `.env`:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
# → 4a7f3c8e1b2d...
```

```env
VDX_VIEW_TOKEN_SECRET=4a7f3c8e1b2d...
```

**Sem `VDX_VIEW_TOKEN_SECRET`:**
- Dev (sem `VDX_API_MASTER_KEY`): gera segredo efêmero com aviso nos logs
- Produção (com `VDX_API_MASTER_KEY`): falha na inicialização com `ValueError`

### Segurança

- Dimensões e tipologia ficam na assinatura HMAC-SHA256 — o receptor não pode alterar parâmetros
- Tokens expirados retornam página HTML amigável (não JSON)
- Rate limit: 30 tokens/minuto por IP no endpoint `/token`, 60 views/minuto no viewer
- Zero API key em query strings — o token tem propósito único (`typ: "view"`)

---

## Monitoramento

### Health checks

```bash
# Básico
curl http://localhost:8000/health

# Detalhado (DB, dependências, sistema)
curl http://localhost:8000/health/detailed -H "X-VDX-Key: $VDX_API_MASTER_KEY"
```

### Logs

```bash
# Log de aplicação (erros, eventos)
tail -f logs/vdx.log

# Log de acesso (cada request)
tail -f logs/access.log

# Log de backup
tail -f ~/backups/vdx/backup.log
```

---

## Troubleshooting

### App não inicia

```bash
# Verificar import limpo
source .venv/bin/activate
python -c "from app.main import app; print('OK')"

# Ver erro completo
uvicorn app.main:app --port 8000 2>&1 | head -30
```

### Banco corrompido

```bash
# Verificar integridade
sqlite3 data/constitution.db "PRAGMA integrity_check;"

# Se falhar: restaurar do backup mais recente
ls -lt ~/backups/vdx/constitution_*.db | head -5
```

### Catalog loader falhando para um fabricante

O loader é resiliente — se um fabricante tem JSON corrompido, os outros continuam carregando.
Verificar qual falhou:

```bash
python -m tools.catalog_loader --stats 2>&1 | tail -20
```

Para recarregar apenas o fabricante com problema após corrigi-lo:

```bash
python -m tools.catalog_loader --fabricante HE
```
