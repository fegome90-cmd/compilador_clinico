# Guía de archivos del compilador clínico

Esta guía explica el checkout vivo de `compilador_clinico` desde sus tipos más bajos hasta el CLI. Está pensada para Felipe: primero presenta el recorrido normal, después define los conceptos y finalmente permite localizar cada módulo, clase, función y constante importante.

> **Estado del informe:** observado el 2026-08-29. Es una descripción estática del árbol de trabajo actual; no es un informe de calidad ni una autorización de entrega.

## Cómo leer esta guía

1. Empieza por el [recorrido de una compilación](#recorrido-de-una-compilacin).
2. Sigue la [ruta recomendada de aprendizaje](#ruta-de-lectura-recomendada).
3. Usa el inventario por archivo como referencia de consulta.
4. Lee las [discrepancias verificadas](#discrepancias-verificadas-documentacin-frente-a-checkout) antes de asumir que una frase histórica del SDD describe el estado actual.

## Alcance y evidencia

- Se inspeccionaron los 22 archivos Python actuales bajo `src/clinical_compiler/`, además de `py.typed`, los inicializadores de paquete, tests, fixtures, goldens, configuración y documentos de arquitectura.
- Se usaron lectura directa, numeración de líneas, `ast.parse` y búsquedas estructurales con `ast-grep`.
- Las referencias de líneas corresponden al checkout observado y son aproximadas cuando el módulo puede seguir cambiando.
- El estado Git observado fue `main...origin/main [ahead 7]`, con modificaciones, borrados y archivos no trackeados. Por eso “presente en el checkout” no significa “committed”.
- No se modificó ningún archivo distinto de este documento nuevo.

## Mapa mental: de JSONL a documento

```text
INPUT bytes (JSONL)
  │
  ▼
adapters/structured_feed.py + adapters/contract.py
  │  FeedEvaluation / StructuredFeedFact / SourceFactIR
  ▼
passes/input_validation.py
  │  SourceFactIR validado; cuarentena de contrato/tipos
  ▼
passes/semantic_normalization.py
  │  CanonicalClinicalFact; missingness; certainty UNRESOLVED; conflictos
  ▼
adapters/seed.py + passes/admissibility.py
  │  política resuelta, veto y provenance contra supervivientes
  ▼
core/ir.py: CanonicalClinicalIR
  │
  ▼
passes/document_selection.py
  │  DocumentIR: referencias y roles, nunca valores
  ▼
renderers/deterministic.py
  │  bytes UTF-8 deterministas
  ▼
linter/conformance.py
  │  bytes aceptados solo si cumplen el modo
  ▼
pipeline.py → cli.py
     documento a stdout/--output; diagnósticos a stderr; exit code
```

El orden está compuesto por `pipeline.run` (`src/clinical_compiler/pipeline.py:188-268`) y se describe normativamente en `openspec/specs/` y `docs/agent/ARCHITECTURE.md` (con registro histórico en `openspec/changes/archive/2026-08-29-clinical-compiler-r1/design.md`).

## Glosario esencial

| Concepto | Significado en este proyecto |
|---|---|
| **IR** | *Intermediate Representation*: representación intermedia. La escalera es `SourceFactIR → CanonicalClinicalFact → CanonicalClinicalIR → DocumentIR → bytes`. Cada salto reduce ambigüedad y cambia la autoridad de los datos. |
| **Fail-closed** | Si hay una condición no segura o un diagnóstico, no se emite documento. Un resultado limpio bajo política resuelta debe producir documento; un resultado vacío sin diagnóstico solo es legal para política no resuelta. |
| **Cuarentena** | Un hecho que falla un stage se retira de los supervivientes y deja un `Diagnostic`; los demás hechos continúan. La acumulación sigue siendo de ejecución completa, no de éxito parcial. |
| **Missingness** | Semántica de presencia: `PRESENT`, ausencia evaluada (`MISSING`, `NOT_APPLICABLE`) o ausencia no evaluada (`UNKNOWN`, `NOT_ASSESSED`). Nunca se deben confluir. |
| **Certainty** | Taxonomía de certeza. En R1 el compilador asigna siempre `UNRESOLVED`; una certeza declarada por la fuente es otra dimensión y se conserva verbatim en el wrapper del adapter. |
| **Provenance** | `source_kind` + `source_ref`: de dónde viene el valor. No prueba por sí sola la verdad clínica ni sustituye a `certainty`. |
| **Determinismo** | La misma entrada produce los mismos bytes, IDs y diagnósticos: tuplas, orden explícito por codepoint, formato sin locale, UTF-8/LF y SHA-256. |
| **PolicyResolution** | Estado de la política D7: seed poblado, vacío aprobado por `DEFERRED_BY_OWNER`, o `UNRESOLVED_POLICY`. El último bloquea antes de admissibility. |

## Recorrido de una compilación

### Ruta exitosa

| Paso | Código | Entrada → salida | Resultado |
|---:|---|---|---|
| 1 | `parse_feed` | `bytes` → `FeedEvaluation` | JSONL decodificable; cada línea válida se mapea al contrato. |
| 2 | `run_input_validation` | `SourceFactIR` → `StageResult[SourceFactIR]` | Sobreviven hechos con forma y tipos válidos. |
| 3 | `run_semantic_normalization` | hechos → `CanonicalClinicalFact` | Se fusionan corroboraciones; certainty=`UNRESOLVED`; `None`→`MISSING`. |
| 4 | `run_admissibility` | canonical facts + seed + IDs fuente → canonical facts | No hay veto ni referencias huérfanas. |
| 5 | `CanonicalClinicalIR` | hechos admitidos → agregado ordenado | IDs únicos y referencias no vacías. |
| 6 | `run_document_selection` | agregado + modo → `DocumentIR` | Una entrada por fact, solo ID y role. |
| 7 | `render_document` | `DocumentIR` + agregado → bytes | Líneas ordenadas y campos sin fact como `unknown [not_assessed]`. |
| 8 | `lint_conformance` | bytes + modo → mismos bytes | El linter acepta únicamente salida limpia. |
| 9 | `_emit` | `CompileResult` → stdout o archivo | Documento emitido y exit `0`. |

### Ruta fallida

| Situación | Diagnóstico/estado | Qué continúa | Salida |
|---|---|---|---|
| Línea JSON inválida o clave desconocida | `INPUT_CONTRACT_ERROR` | Los otros registros válidos | No se emite documento; normalmente exit `3`. |
| Tipo no permitido, incluido `bool` para `FC` | `TYPE_ERROR` | Los otros hechos | No se emite documento; exit `4` si es el diagnóstico más temprano. |
| Dos interpretaciones para el mismo campo | `SEMANTIC_AMBIGUITY_BLOCK` | Otros campos no conflictivos | El grupo conflictivo no crea canonical fact; exit `5` si corresponde. |
| Veto o provenance no resoluble | `POLICY_VIOLATION` / `PROVENANCE_ERROR` | Otros canonical facts | El fact se cuarentena; no se emite documento. |
| Todos los hechos desaparecen | `DOCUMENT_SELECTION_ERROR` | No renderiza | Se enumeran también los diagnósticos upstream; gana el menor código. |
| Inconsistencia interna del IR | `RENDER_ERROR` | No ejecuta linter | Ningún documento parcial; exit `9`. |
| Bytes con formato inválido | `LINT_FAILURE` | No hay documento final | Exit `10`. |
| Seed dado pero inválido | `UNRESOLVED_POLICY` | No ejecuta `pipeline.run` desde el CLI | Error de uso, exit `2`. |

La precedencia de diagnósticos es el mínimo código entre `3` y `10`, en orden de stage, no el orden de declaración del enum (`README.md:246-264`).

# Inventario completo de producción

## Core: tipos y datos de dominio

### `src/clinical_compiler/core/types.py:1-70`

**Imports relevantes:** `dataclass`, `StrEnum` y `Any` (`:3-5`).

| Símbolo | Líneas | Qué hace |
|---|---:|---|
| `Certainty` | `:8-24` | Enum de siete estados: `CANDIDATE`, `UNRESOLVED`, `LIKELY`, `UNLIKELY`, `CONFIRMED`, `PROBABLE`, `AMBIGUOUS`. Se conservan estados para compatibilidad, pero R1 solo produce `UNRESOLVED`. |
| `Missingness` | `:27-39` | Enum de presencia: `UNKNOWN`, `PRESENT`, `MISSING`, `NOT_ASSESSED`, `NOT_APPLICABLE`. |
| `Provenance` | `:42-53` | Dataclass congelada con `source_kind` y `source_ref`. |
| `ClinicalValue` | `:56-70` | Dataclass congelada con `value: Any`, certainty, missingness y provenance. |

No hay funciones ni métodos escritos por el proyecto en este módulo. Los métodos estándar de dataclass son generados por Python.

### `src/clinical_compiler/core/ir.py:1-132`

**Imports relevantes:** `dataclass`, `ClinicalValue` y `Provenance` (`:3-5`).

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `SourceFactIR` | `:8-22` | Dataclass congelada. Conserva `fact_id`, `field_id`, `raw_value: object` y provenance verbatim. Es la frontera de datos de fuente; no interpreta. |
| `CanonicalClinicalFact` | `:25-41` | Dataclass congelada. Lleva `clinical_fact_id`, `field_id`, `ClinicalValue` y `source_fact_refs`. |
| `DocumentEntry` | `:44-56` | Dataclass congelada. Lleva solo `clinical_fact_ref` y `presentation_role`; nunca valores clínicos. |
| `DocumentIR` | `:59-72` | Dataclass congelada con modo y tupla de entradas. Mantiene una sola autoridad para el valor: el canonical fact. |
| `CanonicalClinicalIR` | `:75-100` | Agregado congelado con slots; cruza la frontera admissibility→selection con `facts: tuple[...]`. |
| `CanonicalClinicalIR.__post_init__` | `:102-132` | Rechaza IDs duplicados y refs vacíos, luego ordena por `(field_id, clinical_fact_id)`. Lanza `ValueError` ante esos invariantes. La existencia de cada ref en las fuentes se comprueba más tarde en admissibility, porque este agregado no recibe el mapa de fuentes. |

### `src/clinical_compiler/core/diagnostics.py:1-36`

**Imports relevantes:** `dataclass`, `StrEnum` (`:3-4`).

- `DiagnosticCode` (`:7-21`): enum cerrado de ocho categorías.
- `Diagnostic` (`:24-36`): dataclass congelada con slots: `code`, `message`, `path: str | None`.

No hay funciones propias. Las construcciones de dataclass son automáticas.

### `src/clinical_compiler/core/policy.py:1-9`

No tiene imports ni funciones.

- `NEVER_AUTO_TERMS` (`:3`): `frozenset()` vacío, valor por defecto del core.
- La política efectiva no se escribe aquí: llega a `run_admissibility` como parámetro.

### `src/clinical_compiler/core/__init__.py`

Archivo vacío de paquete (`0 bytes`). No contiene lógica.

## Contrato de stages

### `src/clinical_compiler/pipeline_types.py:1-33`

**Imports relevantes:** `dataclass`, `Generic`, `TypeVar`, `Diagnostic` (`:10-13`).

- `_T` (`:17`): variable genérica.
- `StageResult[_T]` (`:20-33`): dataclass congelada con slots y dos tuplas:
  - `admitted`: supervivientes para el siguiente stage;
  - `diagnostics`: fallos producidos por el stage.

No tiene `__post_init__`; el proyecto exige la forma correcta por contrato y tests. `pipeline.py` lo reexporta (`pipeline.py:75,78-84`).

## Adapters

### `src/clinical_compiler/adapters/contract.py:1-240`

**Imports relevantes:** `Mapping`, `dataclass`, `MappingProxyType`, `Final`, `cast` y `Diagnostic`, `SourceFactIR`, `Certainty`, `Provenance` (`:25-32`).

**Constantes:**

- `CONTRACT` (`:64-69`): `FC` acepta exactamente `int` o `float`; `TA` exactamente `str`.
- `REQUIRED_RECORD_KEYS` (`:71-73`): `fact_id`, `field_id`, `raw_value`, `provenance`.
- `OPTIONAL_RECORD_KEYS` (`:74-76`): `source_asserted_certainty`.
- `ALLOWED_RECORD_KEYS` (`:77-79`).
- `REQUIRED_PROVENANCE_KEYS` (`:80-82`): `source_kind`, `source_ref`.
- `ALLOWED_SOURCE_KINDS` (`:83-85`): `monitor`, `lab`, `clinical_note`.

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `FieldContract` | `:48-61` | Dataclass congelada que declara el campo y sus tipos exactos. Usa `type(value)`, no `isinstance`, para no aceptar `bool` como `int`. |
| `StructuredFeedFact` | `:88-102` | Dataclass congelada con `fact: SourceFactIR` y `source_asserted_certainty: Certainty | None`. |
| `ContractEvaluation` | `:105-116` | Dataclass congelada que pretende representar exactamente `fact XOR diagnostic`. El constructor no impone ese XOR por sí mismo. |
| `_reject(code, message)` | `:119-121` | `DiagnosticCode + str → ContractEvaluation`; construye un rechazo con un único `Diagnostic`. La llama `map_record`. |
| `map_record(record)` | `:124-240` | `object → ContractEvaluation`. Comprueba mapping, claves, identificadores, campo, provenance, certainty opcional y tipo exacto de `raw_value`; `None` es válido. En éxito construye `SourceFactIR` y `StructuredFeedFact`; en fallo llama `_reject`. Es pura y no hace I/O. |

`map_record` es llamado por `parse_feed` y directamente por tests de contrato.

### `src/clinical_compiler/adapters/structured_feed.py:1-93`

**Imports relevantes:** `json`, `dataclass`, diagnósticos y `ContractEvaluation/map_record` (`:30-35`).

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `FeedEvaluation` | `:40-53` | Resultado congelado del feed: evaluaciones por línea y posible diagnóstico de bytes. |
| `parse_feed(data)` | `:56-93` | `bytes → FeedEvaluation`. Decodifica UTF-8; bytes inválidos producen un diagnóstico de feed y cero registros. Para cada línea no vacía ejecuta `json.loads`, registra JSON inválido con línea y llama `map_record`. Conserva orden y permite que otras líneas sobrevivan. |

No abre archivos: recibe bytes ya leídos por el CLI. La llaman `pipeline.run`, `golden_machinery.compile_feed` y los tests.

### `src/clinical_compiler/adapters/seed.py:1-297`

**Imports relevantes:** `json`, `dataclass`, `StrEnum`, `Path`, `Final` (`:64-68`).

**Enums/constantes:**

- `PolicyResolutionState` (`:82-88`): `POPULATED`, `APPROVED_EMPTY_BY_DEFERRAL`, `UNRESOLVED_POLICY`.
- `PolicySeedFault` (`:90-99`): seis razones tipadas de seed inválido.
- `DEFERRED_BY_OWNER_DECISION` (`:101-109`), `_DEFERRAL_MARKER` y `_SEED_TERMS_KEY` (`:112-113`).

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `PolicyResolution` | `:116-176` | Dataclass congelada con estado, términos, fault, detalle y cita de deferral. |
| `PolicyResolution.is_resolved` | `:144-147` | Propiedad: falso solo en `UNRESOLVED_POLICY`. La usan `pipeline.run`, `CompileResult` y la CLI. |
| `PolicyResolution.__post_init__` | `:149-176` | Valida combinaciones legales de campos y lanza `ValueError` si el estado está mal formado. |
| `populated_policy(terms)` | `:179-187` | `frozenset[str] → PolicyResolution(POPULATED)`. |
| `unresolved_policy(fault, detail)` | `:190-198` | Fault tipado + detalle → resolución bloqueada sin términos. |
| `approved_empty_by_deferral(decision_record)` | `:201-224` | Crea el conjunto vacío aprobado solo si la cita contiene `DEFERRED_BY_OWNER`; sin cita lanza `ValueError`. |
| `load_policy_seed(path)` | `:227-297` | Lee UTF-8 y valida exactamente `{"terms": [...]}`. Convierte errores de archivo, JSON, forma y términos a `UNRESOLVED_POLICY`; duplica términos en `frozenset`. Tiene I/O de lectura, pero no juicio clínico. |

La CLI llama `_resolve_policy`, que selecciona entre `approved_empty_by_deferral` y `load_policy_seed` (`cli.py:171-181`). Los tests y la golden machinery también construyen resoluciones directamente.

## Passes puros

### `src/clinical_compiler/passes/input_validation.py:1-110`

**Imports relevantes:** `CONTRACT`, `ALLOWED_SOURCE_KINDS`, diagnósticos, `SourceFactIR`, `Provenance`, `StageResult` (`:25-29`).

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `_violation(fact)` | `:34-86` | `SourceFactIR → Diagnostic | None`. Repite el orden de `map_record`: IDs, campo, provenance y tipo exacto. Devuelve solo el primer error. |
| `run_input_validation(facts)` | `:89-110` | `tuple[SourceFactIR, ...] → StageResult[SourceFactIR]`. Llama `_violation` por fact, conserva identidad y orden de supervivientes y cuarentena cada fallo como `INPUT_CONTRACT_ERROR` o `TYPE_ERROR`. |

### `src/clinical_compiler/passes/semantic_normalization.py:1-156`

**Imports relevantes:** `hashlib`, `json`, diagnósticos, IR, tipos de valor y `StageResult` (`:59-65`).

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `_interpret(fact)` | `:70-80` | `SourceFactIR → (Missingness, object)`. `None` significa `MISSING`; cualquier otro raw value significa `PRESENT`. |
| `_clinical_fact_id(field_id, refs)` | `:83-94` | `str + tuple[str, ...] → str`. Serializa `[field_id, refs]` de forma canónica y calcula SHA-256; no usa tiempo, random ni UUID. |
| `run_semantic_normalization(facts)` | `:97-156` | Agrupa por `field_id`; llama `_interpret`. Conflicto de interpretaciones → un `SEMANTIC_AMBIGUITY_BLOCK` por fact y ningún canonical fact para ese campo. Grupo uniforme → fusiona contribuyentes, ordena refs, conserva provenance del primer fact y llama `_clinical_fact_id`. Siempre asigna `Certainty.UNRESOLVED`. |

La certainty declarada por la fuente no entra a este stage: el pipeline extrae `wrapper.fact` (`pipeline.py:203-218`).

### `src/clinical_compiler/passes/admissibility.py:1-162`

**Imports relevantes:** diagnósticos, `CanonicalClinicalFact`, `StageResult` (`:64-66`).

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `_vetoed_term(fact, veto_terms)` | `:71-84` | Devuelve el término mínimo por codepoint que un valor string contiene; no compara números ni `None`. |
| `_unresolvable_refs(fact, source_fact_ids)` | `:87-99` | Devuelve refs no presentes en los IDs de fuentes supervivientes, ordenadas. |
| `run_admissibility(facts, veto_terms, source_fact_ids)` | `:102-162` | Admite solo facts sin veto y con lineage resoluble. Produce `POLICY_VIOLATION` y/o `PROVENANCE_ERROR`, incluso ambos para un mismo fact; conserva supervivientes sin modificar. No lee `NEVER_AUTO_TERMS`. |

El tercer parámetro `source_fact_ids` es obligatorio en el código actual; completa el sketch de dos parámetros del diseño (`design.md:326-329`).

### `src/clinical_compiler/passes/document_selection.py:1-142`

**Imports relevantes:** diagnósticos, `CanonicalClinicalIR`, `DocumentEntry`, `DocumentIR`, `StageResult` (`:66-72`).

**Constantes:** `NURSING_RECORD_TELEGRAPHIC` (`:81`), `SUPPORTED_MODES` (`:82`) y `TELEGRAPHIC_ENTRY_ROLE` (`:83`).

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `run_document_selection(facts, document_mode)` | `:86-142` | `CanonicalClinicalIR + str → StageResult[DocumentIR]`. Modo desconocido o agregado vacío → `DOCUMENT_SELECTION_ERROR`. En éxito crea una entrada por fact, con ID y role uniforme, nunca el valor. |

La CLI importa desde aquí la lista de modos para que un modo desconocido sea error de uso antes de compilar (`cli.py:69-72,124-128`).

## Renderer y linter

### `src/clinical_compiler/renderers/deterministic.py:1-201`

**Imports relevantes:** `CONTRACT`, diagnósticos, `CanonicalClinicalIR`, `DocumentIR`, `ClinicalValue`, `Missingness`, `StageResult` (`:65-69`).

- `_UNASSESSED_GLYPH` (`:73`): `unknown`.

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `_value_glyph(value)` | `:76-99` | `ClinicalValue → str | None`. Presentes: acepta exactamente `str`, `int` o `float`; `MISSING`→`missing`; `NOT_APPLICABLE`→`not_applicable`; familia no evaluada→`unknown`; tipos sin representación canónica→`None`. |
| `render_document(document, facts)` | `:102-201` | `DocumentIR + CanonicalClinicalIR → StageResult[bytes]`. Resuelve refs, comprueba bijección entrada↔fact, llama `_value_glyph`, ordena líneas por `(field_id, clinical_fact_id)`, añade campos contractuales no evaluados y codifica UTF-8. Cualquier inconsistencia produce `RENDER_ERROR` sin bytes parciales. |

### `src/clinical_compiler/linter/conformance.py:1-262`

**Imports relevantes:** `re`, `Mapping`, `MappingProxyType`, `Final`, contrato, diagnósticos, `Missingness`, `StageResult` (`:74-82`).

**Constantes:** modo y modos soportados (`:86-87`), glyph `unknown` (`:89`), tabla `_FIXED_GLYPHS` (`:94-101`), tokens de missingness/campos (`:102-105`) y regex `_LINE_RE` (`:110-114`).

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `_check_line(line, number)` | `:117-187` | `str + int → list[Diagnostic]`. Comprueba whitespace final, gramática, campo, missingness, glyph y `source_kind`; enumera todos los fallos de una línea en orden estable. |
| `lint_conformance(document, document_mode)` | `:190-262` | `bytes + str → StageResult[bytes]`. Rechaza modo desconocido, newline final incorrecto, `CR`, bytes no UTF-8 y líneas inválidas. Devuelve los mismos bytes solo si no hay `LINT_FAILURE`. |

El linter duplica deliberadamente la tabla de glyphs del renderer para no validar un bug del renderer usando su propia tabla.

## Composición y shell

### `src/clinical_compiler/pipeline.py:1-268`

**Imports relevantes:** dataclasses, `Final`, adapters, cuatro passes, renderer, linter, core y `StageResult` (`:61-76`).

- `_STAGE_ORDER_EXIT_CODES` (`:86-95`): tabla explícita de diagnósticos a exits `3-10`.
- `CompileRequest` (`:104-123`): `data: bytes`, `document_mode: str`, `policy: PolicyResolution`.
- `CompileResult` (`:126-170`): `document: bytes | None`, diagnósticos y política.
- `CompileResult.__post_init__` (`:153-170`): lanza `ValueError` si un documento coexiste con diagnósticos o si una política resuelta produce simultáneamente “sin documento y sin diagnóstico”.
- `derive_exit_code(diagnostics)` (`:173-185`): función pura; calcula el menor exit de la tabla para el conjunto de códigos, o `0` si está vacío.
- `run(request)` (`:188-268`): composición root. Llama a `parse_feed`, validación, normalización, política, admissibility, `CanonicalClinicalIR`, selección, render y lint en orden; detiene el camino de emisión ante cualquier diagnóstico. Una política no resuelta retorna antes de admissibility.

`run` es llamado por el CLI y por `tests/unit/test_pipeline.py`. No tiene `try/except`: la captura de excepción inesperada pertenece a `cli.main`.

### `src/clinical_compiler/cli.py:1-288`

**Imports relevantes:** `argparse`, `os`, `sys`, `tempfile`, `Sequence`, `Path`, `Final`, `NoReturn`, `cast`, adapters de seed, modos y pipeline (`:54-78`).

**Constantes:** exits `0`, `2`, `70` y prefijos de stderr (`:82-87`).

| Símbolo | Líneas | Entrada/salida y comportamiento |
|---|---:|---|
| `_UsageError` | `:90-91` | Excepción interna para errores de invocación que deben acabar en exit `2`. |
| `_Parser.error` | `:94-105` | Sobrescribe argparse: lanza `_UsageError` en vez de llamar directamente a `sys.exit`. |
| `_build_parser()` | `:108-146` | Construye el único comando `compile INPUT [--mode] [--policy-seed] [--output]`. `--mode` usa `SUPPORTED_MODES`. |
| `_format_diagnostic(diagnostic)` | `:149-157` | `Diagnostic → str` en formato `CODE: message (path)`, con path opcional. |
| `_read_input(input_path)` | `:160-168` | `Path → bytes`; un `OSError` se convierte en `_UsageError`. |
| `_resolve_policy(seed_path)` | `:171-181` | Sin seed usa `approved_empty_by_deferral`; con seed llama `load_policy_seed`. |
| `_atomic_write(document, destination)` | `:184-212` | Escribe temporal en el directorio destino, hace flush/fsync, ejecuta `os.replace` y sincroniza el directorio. Limpia el temporal si falla antes del replace. Es la única escritura normal del documento. |
| `_emit(result, output)` | `:215-243` | Envía diagnósticos a stderr y bytes a stdout o `_atomic_write`; calcula exit por `derive_exit_code`; estado inconsistente → `70`. |
| `_execute(namespace)` | `:246-264` | Lee entrada, resuelve seed, transforma política no resuelta en línea `UNRESOLVED_POLICY` + exit `2`, ejecuta `run` y llama `_emit`. |
| `main(argv)` | `:267-288` | Shell pública: retorna entero; `_UsageError`→`2`; excepción inesperada→`70` con mensaje de fail-closed. |

El entry point declarado en `pyproject.toml` es `clinical-compiler = "clinical_compiler.cli:main"` (`pyproject.toml:11-12`). El ejecutable no está materializado en `.venv/bin` en el estado observado porque no se hizo una sincronización.

## Inicializadores y marcador de tipado

| Archivo | Estado y función |
|---|---|
| `src/clinical_compiler/__init__.py:1-5` | Exporta `Diagnostic` y `DiagnosticCode` mediante `__all__`. |
| `src/clinical_compiler/adapters/__init__.py:1` | Docstring de paquete; sin lógica. |
| `src/clinical_compiler/passes/__init__.py:1` | Docstring de paquete; sin lógica. |
| `src/clinical_compiler/linter/__init__.py:1` | Docstring de paquete; sin lógica. |
| `src/clinical_compiler/renderers/__init__.py:1` | Docstring de paquete; sin lógica. |
| `src/clinical_compiler/py.typed` | Marcador PEP 561 vacío; no es un módulo ejecutable. |

Los métodos `__init__`, `__repr__`, `__eq__` y similares de las dataclasses no son funciones escritas por el proyecto. Los únicos métodos explícitos son los enumerados arriba: `CanonicalClinicalIR.__post_init__`, `PolicyResolution.is_resolved`, `PolicyResolution.__post_init__`, `_Parser.error` y `CompileResult.__post_init__`.

# Tests, fixtures, golden machinery y configuración

## Tests

Todos los `test_*` son código de verificación, no lógica del compilador. Sus helpers pueden construir IRs inválidos deliberadamente para probar defensas internas.

### Fixtures compartidos y archivos históricos

- `tests/conftest.py:1-50`: fixtures `make_provenance` y `make_clinical_value`; sus funciones internas `_make` son fábricas de tests.
- `tests/unit/test_contract.py:1-3`: docstring de un draft superseded; no tiene tests activos.

### Core y adapters

- `tests/unit/test_types.py:1-87`: enums, provenance, `ClinicalValue` e inmutabilidad.
- `tests/unit/test_ir.py:1-239`: IR ladder, `DocumentIR` por referencias, agregado canónico, lineage estructural, duplicados y orden.
- `tests/unit/test_diagnostics.py:1-47`: ocho códigos y dataclass `Diagnostic`.
- `tests/unit/test_policy.py:1-43`: `NEVER_AUTO_TERMS` vacío e inmutable.
- `tests/unit/test_adapters_contract.py:1-307`: claves, campos, tipos exactos, `bool`, certainty declarada y determinismo de `map_record`.
- `tests/unit/test_adapters_structured_feed.py:1-292`: JSONL, UTF-8, líneas vacías, errores por línea y cuarentena.
- `tests/unit/test_adapters_seed.py:1-387`: estados D7, faults, deferral, forma legal, deduplicación y wiring de veto.

### Passes

- `tests/unit/test_passes_input_validation.py:1-301`: validación, `TYPE_ERROR`, identidad de supervivientes y orden.
- `tests/unit/test_passes_semantic_normalization.py:1-452`: missingness, certainty, conflictos, fusiones, provenance e IDs estables.
- `tests/unit/test_passes_admissibility.py:1-481`: veto inyectado, containment, independencia de certainty, provenance y cuarentena.
- `tests/unit/test_passes_document_selection.py:1-260`: selección de modo, entradas por referencia, role y fallos de conjunto vacío.

### Renderer, linter, integración, pipeline y CLI

- `tests/unit/test_renderers_deterministic.py:1-402`: glyphs, UTF-8/LF, orden, SHA-256, refs huérfanas, omisiones y tipos no renderizables.
- `tests/unit/test_linter_conformance.py:1-521`: gramática, vocabularios, newline, `CR`, whitespace, glyphs y enumeración de violaciones.
- `tests/unit/test_integration_feed_validation.py:1-293`: adapter → validación.
- `tests/unit/test_integration_phase2_chain.py:1-488`: feed → validación → normalización → admissibility → `CanonicalClinicalIR`.
- `tests/unit/test_integration_phase3_chain.py:1-455`: selección → render → lint, PC-1, PC-2 y fail-closed.
- `tests/unit/test_pipeline.py:1-600`: composición real, política no resuelta, precedencia de exits, spies e inyección de faults de render/lint.
- `tests/unit/test_cli.py:1-657`: argparse, exits `0/2/3-10/70`, stderr, escritura atómica y política.
- `tests/unit/test_integration_golden_determinism.py:1-507`: manifests, drift, evidencia `VALID/DEGRADED/INVALID` y subprocesses con hash seeds.

Los módulos de integración están físicamente bajo `tests/unit/`; no existe `tests/integration/`. Los módulos Phase 2, Phase 3 y golden declaran intención de integración mediante pytest markers en sus encabezados.

## Fixture de política

`tests/fixtures/policy-seed-sample.json:1` es el único archivo actualmente bajo `tests/fixtures/`. Contiene dos términos de veto de prueba. Los 12 fault classes y los dos positive controls se construyen principalmente inline en los tests; los controles positivos también tienen escenarios bajo `tests/golden/scenarios/`.

## Golden machinery

`tests/golden/golden_machinery.py:1-525` es tooling de pruebas, no producción.

- Constantes de rutas/schema: `:81-89`.
- `_ensure_src_on_path`: `:92-102`, hace importable `src` en intérpretes aislados.
- `EvidenceIntegrity`: `:105-118`, enum `VALID/DEGRADED/INVALID`.
- `sha256_hex`: `:126-128`, primitiva de digest.
- `lint_clean`: `:131-140`, usa el linter real y devuelve boolean.
- `compile_feed`: `:143-216`, recompone manualmente el chain Phase 3 y falla si aparece cualquier diagnóstico.
- `ScenarioVerification` y `ok`: `:222-239`.
- `load_manifest`: `:242-250`.
- `verify_corpus`: `:253-298`, comprueba existencia, digests y recompilación.
- `GoldenEvidenceAssessment`: `:301-320`.
- `_independent_problem`: `:323-362`, comprueba consistencia del manifest independiente.
- `assess_golden_evidence`: `:365-427`, clasifica la evidencia.
- `generate_corpus`: `:433-496`, **sí escribe** documentos y manifest; no se ejecutó en esta tarea.
- `main`: `:499-521`, CLI `digest`, `verify` y `generate`.

### Artefactos golden

- `tests/golden/manifest.json:1-44`: tres escenarios (`pc1_unassessed_fc`, `pc2_assessed_absence_ta`, `standard_mixed`) con input/document SHA-256.
- `tests/golden/independent/MANIFEST.json:1-47`: expectativas independientes y digests.
- `tests/golden/scenarios/*.input.jsonl`: entradas JSONL de los tres controles.
- `tests/golden/scenarios/*.document.txt`: documentos esperados por la implementación.
- `tests/golden/independent/*.expected.txt`: documentos re-derivados independientemente.

Ejemplos de bytes esperados:

```text
FC: unknown [not_assessed]
TA: 120/80 [present] [monitor m-9]
```

```text
FC: 72 [present] [monitor m-9]
TA: missing [missing] [clinical_note n-1]
```

## Configuración

`pyproject.toml:1-51` define:

- Python `>=3.11` y metadata del paquete (`:5-10`).
- Entry point CLI (`:11-12`).
- Runtime sin dependencias declaradas; las dependencias están solo en `[dependency-groups].dev` (`:14-20`).
- Layout `src` y `py.typed` (`:22-26`).
- `pytest` sobre `tests`, `src` en `pythonpath`, markers y `--strict-markers` (`:28-36`).
- Coverage branch con mínimo `95` (`:38-43`).
- Ruff y mypy strict (`:45-51`).

`.gitignore:1-16` ya incluye `.pi/`, `_ctx/`, `.coverage` y `.mimosa/`.

# Call graph resumido

```text
cli.main
  ├─ _build_parser
  └─ _execute
      ├─ _read_input
      ├─ _resolve_policy
      │   ├─ approved_empty_by_deferral
      │   └─ load_policy_seed
      ├─ pipeline.run
      │   ├─ parse_feed
      │   │   └─ map_record → _reject
      │   ├─ run_input_validation → _violation
      │   ├─ run_semantic_normalization
      │   │   ├─ _interpret
      │   │   └─ _clinical_fact_id
      │   ├─ run_admissibility
      │   │   ├─ _vetoed_term
      │   │   └─ _unresolvable_refs
      │   ├─ CanonicalClinicalIR
      │   ├─ run_document_selection
      │   ├─ render_document → _value_glyph
      │   └─ lint_conformance → _check_line
      └─ _emit
          ├─ _format_diagnostic
          └─ _atomic_write
```

La golden machinery tiene un chain paralelo (`compile_feed`) para validar la determinación del corpus. Los tests llaman los módulos directamente y no forman parte del runtime.

# Discrepancias verificadas: documentación frente a checkout

Estas son **observaciones verificadas**, no fallos declarados sin investigar.

| Observación verificada | Evidencia documental | Evidencia del checkout vivo | Lectura correcta |
|---|---|---|---|
| Documentación que dice “0 bytes” está desactualizada | `design.md:352`, `tasks.md:22,73` | `README.md` tiene 385 líneas y `docs/architecture.md` 179 | Esos textos describen el baseline previo, no el tamaño actual. |
| Directorio de integración planificado no existe | `design.md:350`, `tasks.md:69` | No existe `tests/integration/`; las suites están en `tests/unit/` | Es una desviación de ubicación registrada; no confundir nombre de carpeta con ausencia de cobertura. |
| Descripción de fixtures es histórica | `README.md:90-92` | `tests/fixtures/` solo contiene `policy-seed-sample.json`; goldens están en `tests/golden/` | El corpus de fallos vive mayormente en código de tests. |
| “Committed” no coincide con Git | `README.md:7,213`; manifests llaman committed a los goldens | `cli.py`, `pipeline.py`, `tests/golden/**` y varios tests están no trackeados | “Presente y leído” no implica “committed”. |
| Baseline de `tasks.md` quedó viejo | `tasks.md:21,136-138` | `conftest.py` está limpio/trackeado, fixture tiene contenido y goldens existen | Es una nota de baseline contra `c6578b6`, no una fotografía del árbol actual. |
| Convención `--no-sync` inconsistente | `tasks.md:5,20` la exige | Ejemplos del README (`:120-125,285-293`) la omiten | Para ejecución futura debe prevalecer la restricción del SDD; esta guía no ejecutó esos comandos. |
| Docstring del golden chain es histórica | `tests/golden/golden_machinery.py:10-15` dice que `pipeline.py` aún no existe | `src/clinical_compiler/pipeline.py` sí existe | La machinery conserva texto de la etapa previa y recompone el chain por razones de test. |
| Sketch de interfaces difiere de firmas reales | `design.md:305-329` muestra `str | None` y `run_admissibility(facts, veto_terms)` | El pipeline usa `bytes | None` (`pipeline.py:149`) y admissibility exige `source_fact_ids` (`:102-106`) | El propio código documenta estas lecturas mínimas; son seams de contrato, no detalles que deban inferirse. |
| Seed vacío tiene una diferencia semántica | `docs/architecture.md:99` habla de términos no vacíos | `load_policy_seed` acepta `{"terms": []}` (`seed.py:273-297`); test explícito en `test_adapters_seed.py:154-166` | El comportamiento de seed maneja `EMPTY_TERMS` y `UNRESOLVED_POLICY` cuando el seed no contiene términos o es inválido, requiriendo `DEFERRED_BY_OWNER` si la bandera se omite. |
| Certainty de fuente no llega al documento | `design.md:281-286` separa ambas autoridades | `StructuredFeedFact` la conserva, pero `pipeline.py:203-218` reenvía solo `wrapper.fact` | En R1 la assertion vive en `SourceFactIR.source_asserted_certainty` y se expone en `CompileResult.source_asserted_certainties`; el canonical fact/render solo lleva certainty del compilador, siempre `UNRESOLVED`. |

## Ruta de lectura recomendada

1. `README.md:1-100`: propósito, IR ladder, reglas de determinismo y estructura.
2. `src/clinical_compiler/core/types.py` y `core/ir.py`: datos que no deberían contener lógica de I/O.
3. `core/diagnostics.py`, `core/policy.py` y `pipeline_types.py`: vocabulario de errores, política y contrato de stages.
4. `adapters/contract.py`: contrato de entrada único.
5. `adapters/structured_feed.py` y `adapters/seed.py`: entrada JSONL y resolución D7.
6. Los cuatro módulos de `passes/`, en orden de pipeline.
7. `renderers/deterministic.py` y `linter/conformance.py`: cómo se convierten y validan los bytes.
8. `pipeline.py`: composición y fail-closed.
9. `cli.py`: argparse, emisión, exits y escritura atómica.
10. Tests correspondientes a cada capa; después `tests/golden/golden_machinery.py` para entender la evidencia de determinismo.
11. `docs/agent/ARCHITECTURE.md`, `docs/architecture.md` (stub), `openspec/specs/` y el archivo histórico `openspec/changes/archive/2026-08-29-clinical-compiler-r1/` al final, separando diseño normativo, plan histórico y checkout vivo.

## Limitaciones

- No se ejecutaron tests, coverage, mypy, ruff, golden verification ni el CLI.
- No se ejecutaron instaladores, `uv sync`, comandos de red ni procesos de runtime.
- Este documento no afirma `PASS` actual, readiness, integridad actual de goldens ni que el working tree sea entregable.
- Los números históricos como `337 passed`, `406 passed` o `100%` se citan solo como contenido de artefactos previos; requieren una nueva ejecución para ser evidencia actual.
- Las líneas son referencias al estado observado y pueden desplazarse cuando se modifique el checkout.

## Key Learnings:

1. La arquitectura separa una hoja de dominio inmutable, adapters de entrada, passes puros, composición y shell de entrega.
2. `source_asserted_certainty`, `compiler_assigned_certainty`, missingness y provenance son ejes distintos; el documento no debe inventar ni confluir ninguno.
3. La seguridad del pipeline depende tanto de la cuarentena por fact como del gate global que impide emitir cualquier documento con diagnósticos.
4. El checkout vivo y los documentos SDD no son la misma autoridad temporal: el estado Git y las líneas actuales deben prevalecer para explicar qué existe hoy.
