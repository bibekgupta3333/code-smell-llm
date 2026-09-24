<!--
Output schema. Concatenated at the {OUTPUT_SCHEMA} placeholder.
The keys here are the exact column names of
prepared_data/datasets/*/occurrences/*.csv so grading is a direct join.
-->

## Output Format (STRICT)

Return a **single JSON object** — no markdown fences, no prose, no commentary
before or after. The runner parses your response with `json.loads` on the
first `{` … matching `}` it finds; anything else is a parse error and counts
as a failed run.

### Schema

```json
{
  "language":   "java | python | javascript | cpp",
  "file_path":  "<echo of input file_path>",
  "class_name": "<top-level class or module name>",
  "findings": [
    {
      "smell_type": "<one of the 23 canonical names; see taxonomy>",
      "category":   "Bloaters | Object-Orientation Abusers | Change Preventers | Dispensables | Couplers",
      "method":     "<method/function name, or 'Entire Class' for class-level smells>",
      "line_start": <integer, 1-indexed, inclusive>,
      "line_end":   <integer, 1-indexed, inclusive>,
      "evidence":   "<one short sentence (≤ 25 words) citing specific code>"
    }
  ]
}
```

### Rules

1. **Empty findings allowed.** `"findings": []` is the correct answer for
   clean code. Prefer omission over fabrication.
2. **No duplicates.** At most one finding per `(method, smell_type)` pair.
   Before emitting, scan your `findings` array and drop any pair that
   already appears earlier in the array.
3. **`smell_type` is a leaf, never a category.** Values like `"Bloaters"`,
   `"Couplers"`, `"Object-Orientation Abusers"`, `"Change Preventers"`,
   `"Dispensables"` are **categories** — putting them in `smell_type` is
   a parse error. `smell_type` must be one of the 23 leaf names from the
   taxonomy (e.g. `"Long Method"`, `"Feature Envy"`).
4. **`category` must match `smell_type`.** Each leaf belongs to exactly
   one category; copy it from the taxonomy header, do not guess.
5. **Lines are 1-indexed, inclusive.** Use the `   N| ` prefix in the input.
   `line_start` ≤ `line_end`. The range must be the **smallest** span that
   contains the evidence.
6. **Cap.** Emit at most **50 findings** per file. If more would qualify,
   keep only the strongest-evidence ones.
7. **Canonical names only.** Use exactly the 23 names from the taxonomy.
   The grader uses string equality.
8. **Method naming conventions:**
   - **Java / C++** — simple method name, no parameters (e.g. `bakePizza`).
   - **Python** — function/method name (e.g. `order_drink`); for
     module-level functions, set `class_name = "<module>"`.
   - **JavaScript** — function name; for arrow functions assigned to a
     name, use the binding name; for anonymous callbacks, use `<anonymous>`.
   - **Class-level smells** (Large Class, Lazy Class, Data Class,
     Alternative Classes with Different Interfaces) — set
     `method = "Entire Class"`.
9. **Evidence sentence** must reference observable code (an identifier, a
   keyword, a count) — not your reasoning. Bad: *"this looks complex"*.
   Good: *"35-LOC body with four unrelated `println` blocks at lines 63–97."*
