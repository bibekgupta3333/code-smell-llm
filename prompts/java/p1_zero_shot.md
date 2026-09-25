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

<!-- USER -->
## Task

Detect every code smell in the Java source file below. Apply the
taxonomy and the output schema exactly. Emit JSON only.

## Input

- `language`:   java
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```java
{SOURCE_CODE}
```

Respond with the JSON object only.
