<!-- SYSTEM -->
{SYSTEM_BLOCK}

{TAXONOMY}

{OUTPUT_SCHEMA}

## Language-specific guidance (Python)

- A *method* is any `def` (including `async def`) at class scope;
  module-level `def` is a *function* — use the function name as
  `method` and the module name as `class_name`.
- Dunder methods (`__init__`, `__repr__`, …) do **not** count as
  Long Method unless their bodies are unusually large.
- A class consisting only of dataclass fields + property
  accessors is `Data Class`.
- Decorators are part of the method header, not its body, when
  computing line ranges and LOC.

<!-- USER -->
## Task

Detect every code smell in the Python source file below. The worked
examples below illustrate the **format and decision threshold**: copy their
structure, do not copy their findings. Note that one example deliberately
shows clean code with `findings: []` — emit `[]` when uncertain.

## Worked examples (Python)

{FEW_SHOT_EXAMPLES}

## Now analyse this file

- `language`:   python
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```python
{SOURCE_CODE}
```

Respond with the JSON object only.
