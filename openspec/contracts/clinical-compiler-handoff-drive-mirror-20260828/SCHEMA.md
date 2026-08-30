---
id: ai-work-wiki-schema
title: AI Work Wiki · Frontmatter Contract
type: schema
status: active
version: "0.1"
tags: [ai-work, wiki, yaml, schema]
---
# Frontmatter Contract
Campos mínimos por documento:
- `id`: identificador estable, independiente del filename.
- `project`: familia/proyecto.
- `authority`: autoridad documental.
- `document_tier`: D0–D3.
- `status`: active / draft / historical / superseded.
- `migration_state`: source-backed / artifact-backed.
- `canonical.control_plane`: `wiki`.
- `canonical.content`: `editable-source` o `pdf-temporary`.
- `canonical.pdf_generation`: `on-demand`.
- `artifact`: snapshot PDF existente.
- `relationships`: enlaces semánticos (`complements`, `uses`, `governed_by`, `related_to`, etc.).
- `audit`: baseline y findings.
- `freshness`: solo cuando el contenido depende de estado externo mutable.
Invariantes:
1. Un tier nunca otorga autoridad.
2. Un PDF no se vuelve fuente canónica por ser más nuevo.
3. `pdf-temporary` es un estado de migración, no el estado objetivo.
4. Los IDs de relaciones deben resolver a notas existentes.
5. Una relación `complements` no implica supersesión.
