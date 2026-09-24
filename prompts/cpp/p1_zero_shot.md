<!-- SYSTEM -->
{SYSTEM_BLOCK}

{TAXONOMY}

{OUTPUT_SCHEMA}

## Language-specific guidance (C++)

- Header (`.h`) and implementation (`.cpp`) of the same class are
  analysed independently per file. If the same smell occurs in
  both, emit one finding per file.
- Inline definitions in headers count toward the header file's
  LOC, not the implementation's.
- Templates: count the body of the primary template once;
  explicit specialisations are separate methods.
- `friend` declarations and direct private-member access from
  another class are strong evidence of `Inappropriate Intimacy`.

<!-- USER -->
## Task

Detect every code smell in the C++ source file below. Apply the
taxonomy and the output schema exactly. Emit JSON only.

## Input

- `language`:   cpp
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```cpp
{SOURCE_CODE}
```

Respond with the JSON object only.
