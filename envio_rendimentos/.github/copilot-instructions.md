# Envio de Rendimentos - AI Coding Agent Instructions

## Project Overview
**Envio de Rendimentos** is a Django 5.2 application for managing creditors (credores), generating PDFs from financial data, and sending emails with attachments. It processes PGC (Pedidos de Grupamento de Crédito) spreadsheets containing commission/income data, normalizes creditor names, and distributes personalized financial documents.

### Key Technologies
- **Backend**: Django 5.2 + SQLite
- **Data Processing**: pandas, openpyxl (Excel), WeasyPrint (PDF generation)
- **Email**: Django EmailMessage with Outlook/O365 SMTP
- **Frontend**: Django templates
- **Deployment**: Docker with docker-compose

---

## Architecture & Data Flow

### Core Models ([core/models.py](core/models.py))
- **Credor**: Creditor with normalized name, email, period, send status. `nome_normalizado` is auto-computed on save.
- **Rendimento**: Income records linked to Credores via FK, stores period + amount.
- **HistoricoPGC**: Audit log of PGC distributions (PGC number, period, total value).
- **Grupo**: Groups for organizing creditors.
- **EmpresaPagadora**: Paying company metadata (short name, CNPJ).

### View Layers ([core/views.py](core/views.py) - 1246 lines)
**Dashboard/List Views**: `index`, `dashboard`, `listar_Credores` (paginated list, searchable)

**File Upload Flows**:
- `upload_planilha`: Upload PGC spreadsheet → `salvar_planilha_temporaria()` → processed via `normalizar_planilha_origem()`
- `upload_emails`: Upload creditor email mappings → parsed into database

**Creditor CRUD**: `adicionar_credor`, `editar_Credor`, `excluir_Credor`, `listar_Credores`

**Email/Batch Operations**:
- `enviar_emails_view`: Sends emails with attached PDFs/spreadsheets in threads
- `enviar_emails_selecionados`: Batch sends for selected creditors
- `exportar_Credores_excel`: Exports creditor list

**Specialized Workflows**:
- `laghetto_sports_view`: Custom PGC processing for "Laghetto Sports" (uses async `request_id` tracking)
- `lgm_view`: Alternative PGC processor with different normalization rules

### Utilities Organization

**[core/utils.py](core/utils.py) - Core business logic** (683 lines)
- `normalizar_nome()`: Removes leading numbers, parentheses, accents; converts to uppercase
- `normalizar_planilha_origem()`: Renames column headers (dates), saves treated Excel
- `normalizar_colunas_com_duas_linhas()`: Flattens multi-line headers (used for PGC sheets)
- `extrair_minimos_robusto()`: Extracts minimum guaranteed values from spreadsheets
- `gerar_pdf_relatorio()`: Renders Django template + WeasyPrint → PDF
- `enviar_email_com_arquivos()`: Composes & sends emails via Django EmailMessage
- **Logger**: File-based logger to `media/envios.log`

**[core/normalizacao.py](core/normalizacao.py) - Name normalization**
- `normalizar_nome()`: Standalone implementation (used in models + services)

**[core/utils_files.py](core/utils_files.py) - File I/O isolation**
- Each workflow has isolated temp folder functions to prevent conflicts
- Example: `salvar_planilha_temporaria_lgm()` → `media/tmp_lgm/`

**[core/utils_progress.py](core/utils_progress.py) - Async progress tracking**
- Thread-safe `_PROGRESS_STORE` dict keyed by UUID `request_id`
- Functions: `init_progress()`, `log_progress()`, `set_progress()`, `finish_progress()`
- Stores: status, percent, processed count, current creditor name, logs with timestamps

**[core/utils_lgm.py](core/utils_lgm.py) - LGM-specific PGC processor**
- `processar_pgc_lgm()`: Main entry point (called from `lgm_view`)
- `carregar_empresas()`: Loads EmpresaPagadora objects
- `localizar_abas()`: Finds sheet names matching patterns (MINIMO, EMISSAO, etc.)
- `ler_minimo()`: Extracts minimum table from specific sheet
- Uses same progress tracking as Laghetto workflow

---

## Project-Specific Patterns & Conventions

### 1. Spreadsheet Processing Strategy
- **Multi-line Headers**: PGC sheets have merged cells across rows 1-4, flattened via `normalizar_colunas_com_duas_linhas()`
- **Column Mapping**: Create rename dicts for known columns (see `renomear` in `normalizar_planilha_origem()`)
- **Safe Conversion**: Always convert columns to string before string operations (`.astype(str)` before `.agg()`)

### 2. Name Normalization Pattern
Names are normalized consistently across the app:
- Remove leading "XX - " patterns (e.g., "2 - ACME Corp" → "ACME CORP")
- Strip parenthetical text: "(Filial)" removed
- Unicode normalization (NFKD) to strip accents
- Uppercase + whitespace collapse
- Used for: DB indexing (`nome_normalizado`), email matching, deduplication

### 3. Temporary File Organization
```
media/
  TEMPORARIOS/          # General temp files (original uploads)
  tmp_lgm/              # LGM workflow temp files (isolated)
  PGC/{numero}/         # Processed PGC output (MINIMO.xlsx, etc.)
  planilhas_originais_tratadas/  # Normalized source sheets
  processing/{uuid}/    # Long-running job work directories
```
**Rule**: Each workflow uses separate folders to avoid concurrent overwrites.

### 4. Progress Tracking for Long Operations
When adding async/threaded operations (e.g., bulk email sends):
1. Call `init_progress()` → returns UUID `request_id`
2. Pass `request_id` to worker thread
3. Worker calls `log_progress(request_id, message)` for logging
4. Worker calls `set_progress(request_id, processed=n, total=t, percent=p, credor=name)`
5. Frontend polls `{view_name}_status` endpoint to fetch progress JSON
6. Call `finish_progress(request_id)` on completion

### 5. Email Sending Pattern
```python
from core.utils import enviar_email_com_arquivos

enviar_email_com_arquivos(
    destinatario="user@example.com",
    assunto="PGC 14 - Envio de documentos",
    corpo_html=render_to_string('template.html', context),
    anexos=["/path/to/file1.pdf", "/path/to/file2.xlsx"]
)
```
Credentials: Outlook SMTP config in settings (EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)

### 6. Django Model Overrides
- Override `save()` to auto-compute derived fields (e.g., `nome_normalizado` in Credor model)
- Use `__str__()` for readable admin/list display
- Use `related_name` for reverse querysets (e.g., `credor.rendimentos.all()`)

### 7. View Response Patterns
- **HTML List**: Use `Paginator` for large result sets, pass `page_obj` to template
- **JSON/AJAX**: Return `JsonResponse({'data': ...})` or status dict
- **File Download**: Use `FileResponse(open(path, 'rb'), as_attachment=True)`
- **Redirects**: Use `redirect('url_name')` with `messages.success/error()` for user feedback

---

## Critical Files by Purpose

| Purpose | File(s) |
|---------|---------|
| **Data Models** | [core/models.py](core/models.py) |
| **Views & Routes** | [core/urls.py](core/urls.py), [core/views.py](core/views.py) |
| **Core Processing** | [core/utils.py](core/utils.py), [core/utils_lgm.py](core/utils_lgm.py) |
| **File I/O** | [core/utils_files.py](core/utils_files.py) |
| **Forms** | [core/forms.py](core/forms.py) |
| **Admin Config** | [core/admin.py](core/admin.py) |
| **Settings** | [envio_rendimentos/settings.py](envio_rendimentos/settings.py) |
| **Standalone Scripts** | [envio_pgc.py](envio_pgc.py) (email distribution), [run.py](run.py) (Django runserver) |

---

## Common Workflows

### Adding a New PGC Processing Workflow
1. Create utility functions in `core/utils_{name}.py` (isolated from main utils)
2. Use `core/utils_progress.py` for tracking
3. Add view in `core/views.py` + URL in `core/urls.py`
4. Create templates in `core/templates/{name}/`
5. Reference existing `laghetto_sports_view` or `lgm_view` as template

### Processing an Uploaded Spreadsheet
1. Save to temp folder via `salvar_planilha_temporaria_*()` in `utils_files.py`
2. Read with `pd.read_excel()`, handle multi-line headers if needed
3. Normalize columns & data types
4. Extract data into model objects or output files
5. Save results to `media/PGC/{numero}/` or similar

### Sending Bulk Emails
1. Iterate over creditors (use `for credor in credores_list`)
2. Call `enviar_email_com_arquivos()` inside thread if async needed
3. Log progress with `log_progress()` before/after each send
4. Handle exceptions, update HistoricoPGC for audit trail

---

## Testing & Debugging

### Running Locally
```bash
python manage.py runserver 0.0.0.0:8000
# or: python run.py (runs migrate + runserver)
```

### Docker
```bash
docker-compose up --build
# Service runs on localhost:8000
```

### Database
- Uses SQLite (`db.sqlite3`)
- Migrations in [core/migrations/](core/migrations/)
- Apply: `python manage.py migrate`
- Reset: Delete `db.sqlite3` and rerun migrate

### Common Debugging
- Check `media/envios.log` for email/processing logs
- Use `logger.debug()`, `logger.info()`, `logger.error()` from utils
- Inspect `media/TEMPORARIOS/` and `media/PGC/` for intermediate files
- Progress tracking: Query `_PROGRESS_STORE` in `utils_progress.py` directly in shell

---

## Gotchas & Important Notes

1. **Accented Characters**: All name matching uses `normalizar_nome()` for consistency. When comparing creditor names from external sources, apply normalization first.

2. **Excel Multi-Header Sheets**: PGC sheets often have merged headers. Always check `header_start` row number and use `normalizar_colunas_com_duas_linhas()` with correct offset.

3. **Thread Safety**: Progress tracking uses `_PROGRESS_LOCK` to prevent race conditions. If adding new shared state, use locks.

4. **File Conflicts**: Each workflow must use isolated temp folders (not shared `TEMPORARIOS`). Concurrent processes overwriting files have caused data loss.

5. **Email Credentials**: Hardcoded in [envio_pgc.py](envio_pgc.py) and [settings.py](envio_rendimentos/settings.py). Move to environment variables before production deployment.

6. **Timezone Awareness**: `django.utils.timezone` imported but may not be used consistently. Use `.now()` for aware datetimes in new code.
