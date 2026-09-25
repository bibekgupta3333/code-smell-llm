<!-- SYSTEM -->
{SYSTEM_BLOCK}

{TAXONOMY}

{OUTPUT_SCHEMA}

## Language-specific guidance (JavaScript)

- A *method* includes: `class` member methods, named functions
  (`function foo() {}`), and arrow functions assigned to a name
  (`const foo = () => {}`).
- For anonymous callbacks emit `method = "<anonymous>"` and use
  the enclosing line range.
- Prototype-based methods (`Foo.prototype.bar = function()`) count
  as methods of `Foo`.

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

Apply the two-pass protocol to the JavaScript source below.

## Input

- `language`:   javascript
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```javascript
{SOURCE_CODE}
```

Respond with `<analysis>...</analysis><answer>...JSON...</answer>`.
