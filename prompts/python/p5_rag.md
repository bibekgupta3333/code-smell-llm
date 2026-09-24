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

## Retrieval policy

The user message contains *retrieved exemplars*: top-k similar smelly
Python snippets from the training corpus, each with their canonical
findings. Use them only to:

1. **Calibrate** your detection threshold — what counts as Long Method,
   Feature Envy, etc., in real Python code.
2. **Disambiguate** taxonomy edge cases by analogy.

Do **not**:

- copy line numbers, method names, or evidence text from the exemplars;
- emit a finding solely because an exemplar had it — apply T1 (Evidence)
  to the *target* file independently;
- echo or summarise the exemplars in your output.

Each exemplar block has the form:

```
### Exemplar {{i}} — file_path={{path}}
<source>
   1| ...
   2| ...
</source>
<findings>
[{{...JSON findings for this exemplar...}}]
</findings>
```

<!-- USER -->
## Retrieved exemplars

{RETRIEVED_SNIPPETS}

## Now analyse this new file

- `language`:   python
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```python
{SOURCE_CODE}
```

Respond with the JSON object only — do not reference the exemplars in your
output.
