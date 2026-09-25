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

## Two-pass self-verification protocol

You will produce two segments wrapped in sentinel tags. The runner discards
the first and grades only the second.

```
<analysis>
... your private working notes ...
</analysis>
<answer>
{{ ...JSON object matching the schema... }}
</answer>
```

### Pass A — draft (inside `<analysis>`)
Read the file and list candidate findings. Be liberal here — recall over
precision.

### Pass B — critique (inside `<analysis>`, after the draft)
For **each** draft candidate apply all four tests; drop the candidate if
*any* test fails:

- **T1 Evidence** — name the specific lines that prove the smell. If you
  cannot, drop.
- **T2 Granularity** — `method` is correctly named (a real method, not a
  loop, not the class for non-class smells). `line_start..line_end` is the
  smallest range containing the evidence.
- **T3 Taxonomy** — `smell_type` is one of the 23 canonical names and
  `category` matches.
- **T4 Non-redundancy** — no other surviving finding has the same
  `(method, smell_type)` key.

Then for every method that survived Pass A *without* a finding, run a
**coverage probe**: explicitly check Long Method, Feature Envy, Message
Chains, Switch Statements, Control Coupling. Add findings only if T1–T4
all pass.

### Final
Inside `<answer>` emit the JSON object only. The grader reads exactly what
is between `<answer>` and `</answer>`.

<!-- USER -->
## Task

Apply the two-pass protocol to the Python source below.

## Input

- `language`:   python
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```python
{SOURCE_CODE}
```

Respond with `<analysis>...</analysis><answer>...JSON...</answer>`.
