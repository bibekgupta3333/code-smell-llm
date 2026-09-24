<!--
Shared smell taxonomy. The runner concatenates this into every prompt at the
{TAXONOMY} placeholder. Do NOT modify the smell names here without also
updating prepared_data/build_dataset.py CATEGORY_OF and the evaluation script.
-->

## Code-Smell Taxonomy (23 canonical smells, Fowler's 5 categories)

You must use **exactly** these smell names. Do not invent new ones.

### Bloaters
- **Long Method** — method body > ~25 LOC or doing > 1 conceptual task.
- **Large Class** — class with > ~10 fields or > ~15 methods or > ~200 LOC, mixing responsibilities.
- **Primitive Obsession** — using primitives (`bool`, `string`, `int`) where a small object/enum would be clearer (e.g. status codes as ints, currency as float).
- **Long Parameter List** — method with ≥ 4 parameters, or ≥ 3 of the same type.
- **Data Clumps** — same group of fields/parameters appearing together repeatedly (e.g. `firstName`, `lastName`, `address`, `phone`, `email`).

### Object-Orientation Abusers
- **Switch Statements** — long `switch`/`if-else-if` chain on a type code; should be polymorphism.
- **Temporary Field** — field that is only meaningful in some object states (set, used briefly, then unused).
- **Refused Bequest** — subclass inherits methods/fields it doesn't use or overrides them with no-ops.
- **Alternative Classes with Different Interfaces** — two classes do similar work but expose different method names/signatures.
- **Parallel Inheritance Hierarchies** — every time you add a subclass to hierarchy A, you must also add one to hierarchy B.

### Change Preventers
- **Divergent Change** — one class changes for many unrelated reasons; should be split.
- **Shotgun Surgery** — one logical change requires edits across many classes/methods.

### Dispensables
- **Comments** — code so unclear that comments are needed to explain what (not why) it does.
- **Duplicate Code** — same/near-same code block appears in ≥ 2 places.
- **Lazy Class** — class that does almost nothing; could be inlined.
- **Data Class** — class with only fields + getters/setters, no behaviour.
- **Dead Code** — method/field/import never used or unreachable.
- **Speculative Generality** — abstractions ("just in case") with no current concrete user.

### Couplers
- **Feature Envy** — method uses another class's data more than its own.
- **Inappropriate Intimacy** — two classes access each other's private internals.
- **Message Chains** — `a.getB().getC().getD()` — chain of method calls digging through objects.
- **Middle Man** — class whose methods only delegate to another class.
- **Control Coupling** — passing a flag/enum that controls which branch of the callee runs.

### Special markers
- `Entire Class` for `method` field when the smell applies to the whole class (e.g. Large Class).

### Strict naming — output the canonical name only

The grader joins on **exact string match**. Use **only** the names above.
The following common variants are **wrong** and will be counted as misses:

| Wrong | Correct |
|---|---|
| `Message Chain` | `Message Chains` |
| `Switch Statement` | `Switch Statements` |
| `Temporary Fields` | `Temporary Field` |
| `Long Parameters List`, `Long Parameters` | `Long Parameter List` |
| `Parallel Inheritance Hierarchy`, `Parallel Inheritance` | `Parallel Inheritance Hierarchies` |
| `Middleman` | `Middle Man` |
| `Inappropriate Intimacies` | `Inappropriate Intimacy` |
| `Unnecessary Comments`, `Useless Comments` | `Comments` |
