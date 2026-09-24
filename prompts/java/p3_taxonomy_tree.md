<!-- SYSTEM -->
{SYSTEM_BLOCK}

{TAXONOMY}

{OUTPUT_SCHEMA}

## Language-specific guidance (Java)

- A *method* is a non-static or static member function inside a `class`.
- Inner / nested / anonymous classes count as separate classes.
- Generated `equals`/`hashCode`/`toString` are not Long Method.
- A class with **only** fields + getters/setters is `Data Class`,
  even if it has a constructor.

## Decision procedure

Walk the following ordered checks. Each check has a **trigger** (an
observable property of the code) and an **action** (emit / skip).
Trigger thresholds are *heuristic anchors*, not hard rules — adjust upward
if the surrounding code uses a comparable style, downward for very small
files.

**Default action is SKIP.** Most checks should not fire on most files.
Only emit when the trigger is concretely satisfied by lines you can cite.
`"→ emit"` is conditional on the trigger — never enumerate the list as
a todo of items to produce. False positives are penalised equally to
false negatives.

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

Apply the decision procedure above to the Java source below. Emit JSON
only.

## Input

- `language`:   java
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```java
{SOURCE_CODE}
```

Before returning, **deduplicate**: keep at most one finding per
`(method, smell_type)` pair, and ensure each `smell_type` is a leaf name
from the taxonomy (never a category like `Bloaters`).

Respond with the JSON object only.
