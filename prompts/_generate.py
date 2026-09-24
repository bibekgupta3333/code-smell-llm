"""Generate the 5 × 4 = 20 language-specific prompt files under prompts/<lang>/.

Each generated file uses two delimiters that the runner splits on:

    <!-- SYSTEM -->
    ... system role content ...
    <!-- USER -->
    ... user role content ...

The runner concatenates `_system.md` into the SYSTEM block and substitutes
`{TAXONOMY}` / `{OUTPUT_SCHEMA}` from the shared files. Per-call placeholders
({FILE_PATH}, {CLASS_NAME}, {SOURCE_CODE}, {FEW_SHOT_EXAMPLES},
{RETRIEVED_SNIPPETS}) are filled in at inference time.

Run once:  python3 prompts/_generate.py
"""
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parent

# ---------- per-language adaptations ----------

LANGS: dict[str, dict[str, str]] = {
    "java": {
        "display": "Java",
        "ext_note": "`.java`",
        "language_notes": (
            "- A *method* is a non-static or static member function inside a `class`.\n"
            "- Inner / nested / anonymous classes count as separate classes.\n"
            "- Generated `equals`/`hashCode`/`toString` are not Long Method.\n"
            "- A class with **only** fields + getters/setters is `Data Class`,\n"
            "  even if it has a constructor."
        ),
    },
    "python": {
        "display": "Python",
        "ext_note": "`.py`",
        "language_notes": (
            "- A *method* is any `def` (including `async def`) at class scope;\n"
            "  module-level `def` is a *function* — use the function name as\n"
            "  `method` and the module name as `class_name`.\n"
            "- Dunder methods (`__init__`, `__repr__`, …) do **not** count as\n"
            "  Long Method unless their bodies are unusually large.\n"
            "- A class consisting only of dataclass fields + property\n"
            "  accessors is `Data Class`.\n"
            "- Decorators are part of the method header, not its body, when\n"
            "  computing line ranges and LOC."
        ),
    },
    "javascript": {
        "display": "JavaScript",
        "ext_note": "`.js`",
        "language_notes": (
            "- A *method* includes: `class` member methods, named functions\n"
            "  (`function foo() {}`), and arrow functions assigned to a name\n"
            "  (`const foo = () => {}`).\n"
            "- For anonymous callbacks emit `method = \"<anonymous>\"` and use\n"
            "  the enclosing line range.\n"
            "- Prototype-based methods (`Foo.prototype.bar = function()`) count\n"
            "  as methods of `Foo`."
        ),
    },
    "cpp": {
        "display": "C++",
        "ext_note": "`.cpp` / `.h`",
        "language_notes": (
            "- Header (`.h`) and implementation (`.cpp`) of the same class are\n"
            "  analysed independently per file. If the same smell occurs in\n"
            "  both, emit one finding per file.\n"
            "- Inline definitions in headers count toward the header file's\n"
            "  LOC, not the implementation's.\n"
            "- Templates: count the body of the primary template once;\n"
            "  explicit specialisations are separate methods.\n"
            "- `friend` declarations and direct private-member access from\n"
            "  another class are strong evidence of `Inappropriate Intimacy`."
        ),
    },
}

# ---------- 5 strategy templates ----------
# Each template uses two delimiters: <!-- SYSTEM --> and <!-- USER -->.
# Curly-brace placeholders are filled by the runner.

P1_ZERO_SHOT = """\
<!-- SYSTEM -->
{SYSTEM_BLOCK}

{TAXONOMY}

{OUTPUT_SCHEMA}

## Language-specific guidance ({DISPLAY})

{LANGUAGE_NOTES}

<!-- USER -->
## Task

Detect every code smell in the {DISPLAY} source file below. Apply the
taxonomy and the output schema exactly. Emit JSON only.

## Input

- `language`:   {LANGUAGE_KEY}
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```{LANGUAGE_KEY}
{SOURCE_CODE}
```

Respond with the JSON object only.
"""


P2_FEW_SHOT = """\
<!-- SYSTEM -->
{SYSTEM_BLOCK}

{TAXONOMY}

{OUTPUT_SCHEMA}

## Language-specific guidance ({DISPLAY})

{LANGUAGE_NOTES}

<!-- USER -->
## Task

Detect every code smell in the {DISPLAY} source file below. The worked
examples below illustrate the **format and decision threshold**: copy their
structure, do not copy their findings. Note that one example deliberately
shows clean code with `findings: []` — emit `[]` when uncertain.

## Worked examples ({DISPLAY})

{FEW_SHOT_EXAMPLES}

## Now analyse this file

- `language`:   {LANGUAGE_KEY}
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```{LANGUAGE_KEY}
{SOURCE_CODE}
```

Respond with the JSON object only.
"""


P3_TAXONOMY_TREE = """\
<!-- SYSTEM -->
{SYSTEM_BLOCK}

{TAXONOMY}

{OUTPUT_SCHEMA}

## Language-specific guidance ({DISPLAY})

{LANGUAGE_NOTES}

## Decision procedure

Walk the following ordered checks. Each check has a **trigger** (an
observable property of the code) and an **action** (emit / skip).
Trigger thresholds are *heuristic anchors*, not hard rules — adjust upward
if the surrounding code uses a comparable style, downward for very small
files. When in doubt, **skip**.

The thresholds below summarise the operationalisations used by Sharma &
Spinellis (2018) and DesigniteJava; they are starting points, not verdicts.

### Pass 1 — class / file scope
1. **Large Class** — class has > 10 fields **or** > 15 methods **or**
   > 200 LOC **and** mixes ≥ 2 unrelated responsibilities. → emit with
   `method = "Entire Class"`.
2. **Lazy Class** — class has < 2 substantive methods (constructors and
   trivial accessors do not count). → emit.
3. **Data Class** — class exposes only fields + getters/setters/equals/
   hashCode/toString. → emit.
4. **Alternative Classes with Different Interfaces** — two classes in the
   file (or an obvious sibling) provide overlapping behaviour through
   differently-named methods. → emit on each.

### Pass 2 — per-method scope (apply to every method/function)
For each method `M`:

5. **Long Method** — body LOC > 25 **or** body covers ≥ 2 conceptual tasks
   (separable by blank lines or comment headers). → emit.
6. **Long Parameter List** — `M` declares ≥ 4 parameters **or** ≥ 3 of
   the same primitive type. → emit.
7. **Switch Statements** — `switch` / chained `if … else if` branching on
   a type/string code with ≥ 3 arms. → emit.
8. **Feature Envy** — `M` references another object's accessors more often
   than its own (`other.x()` count > `this.x()` count). → emit.
9. **Message Chains** — `a.b().c().d()` with ≥ 3 hops, where intermediates
   are not stored locally. → emit.
10. **Middle Man** — `M`'s body is a single delegating call to another
    object's method, with no added behaviour. → emit.
11. **Duplicate Code** — `M`'s body is ≥ 80 % token-identical to another
    method's body in the same file. → emit on each duplicate.
12. **Dead Code** — `M` is never invoked anywhere in the file and is not
    part of a public API contract (no `public`/`@Override` / `__all__`
    export marker). → emit.
13. **Speculative Generality** — `M` exists for an imagined future use, has
    no current caller, and is not part of an interface/abstract base. → emit.
14. **Control Coupling** — `M` accepts a flag (`bool`, enum, magic string)
    that selects which branch runs in its body. → emit.

### Pass 3 — field / cross-cutting scope
15. **Primitive Obsession** — primitive types (`bool`, `int`, `String`)
    used to model concepts that warrant a small class/enum (status,
    currency, identifier, units). → emit per occurrence cluster.
16. **Data Clumps** — same group of ≥ 3 fields/parameters appears together
    in ≥ 2 declarations (constructor + setter, two methods, etc.). → emit
    once per clump.
17. **Temporary Field** — a field is only meaningful in a subset of the
    object's lifecycle (initialised lazily, reset to null after use, or
    relevant only inside one method). → emit.
18. **Inappropriate Intimacy** — class accesses another class's private
    fields/methods directly (e.g., via `friend` in C++, `_x` access in
    Python, package-private in Java). → emit.
19. **Refused Bequest** — subclass overrides inherited methods with empty
    bodies, raises `NotImplementedError`, or ignores parent state. → emit.
20. **Parallel Inheritance Hierarchies** — every subclass added to A forces
    a sibling subclass in B (visible naming pattern). → emit.
21. **Divergent Change** — class would change for ≥ 2 unrelated reasons
    (visible as ≥ 2 thematically distinct method clusters). → emit with
    `method = "Entire Class"`.
22. **Shotgun Surgery** — one logical change requires edits to ≥ 3
    different methods (e.g., per-field setters that always change
    together). → emit per affected method.
23. **Comments** — block/inline comments explain *what* the code does
    rather than *why*, suggesting the code is unclear. → emit.

When all three passes finish, return the JSON object. Do **not** include the
walkthrough; it is a private analysis.

<!-- USER -->
## Task

Apply the decision procedure above to the {DISPLAY} source below. Emit JSON
only.

## Input

- `language`:   {LANGUAGE_KEY}
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```{LANGUAGE_KEY}
{SOURCE_CODE}
```

Respond with the JSON object only.
"""


P4_SELF_VERIFY = """\
<!-- SYSTEM -->
{SYSTEM_BLOCK}

{TAXONOMY}

{OUTPUT_SCHEMA}

## Language-specific guidance ({DISPLAY})

{LANGUAGE_NOTES}

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

Apply the two-pass protocol to the {DISPLAY} source below.

## Input

- `language`:   {LANGUAGE_KEY}
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```{LANGUAGE_KEY}
{SOURCE_CODE}
```

Respond with `<analysis>...</analysis><answer>...JSON...</answer>`.
"""


P5_RAG = """\
<!-- SYSTEM -->
{SYSTEM_BLOCK}

{TAXONOMY}

{OUTPUT_SCHEMA}

## Language-specific guidance ({DISPLAY})

{LANGUAGE_NOTES}

## Retrieval policy

The user message contains *retrieved exemplars*: top-k similar smelly
{DISPLAY} snippets from the training corpus, each with their canonical
findings. Use them only to:

1. **Calibrate** your detection threshold — what counts as Long Method,
   Feature Envy, etc., in real {DISPLAY} code.
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

- `language`:   {LANGUAGE_KEY}
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```{LANGUAGE_KEY}
{SOURCE_CODE}
```

Respond with the JSON object only — do not reference the exemplars in your
output.
"""


TEMPLATES = {
    "p1_zero_shot.md":     P1_ZERO_SHOT,
    "p2_few_shot.md":      P2_FEW_SHOT,
    "p3_taxonomy_tree.md": P3_TAXONOMY_TREE,
    "p4_self_verify.md":   P4_SELF_VERIFY,
    "p5_rag.md":           P5_RAG,
}


def main() -> None:
    for lang, info in LANGS.items():
        out_dir = ROOT / lang
        out_dir.mkdir(exist_ok=True)
        for fname, tmpl in TEMPLATES.items():
            content = (
                tmpl.replace("{DISPLAY}", info["display"])
                    .replace("{LANGUAGE_KEY}", lang)
                    .replace("{LANGUAGE_NOTES}", info["language_notes"])
            )
            (out_dir / fname).write_text(content, encoding="utf-8")
            print("wrote", out_dir / fname)


if __name__ == "__main__":
    main()
