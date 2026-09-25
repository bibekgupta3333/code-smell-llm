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

## Retrieval policy

The user message contains *retrieved exemplars*: top-k similar smelly
C++ snippets from the training corpus, each with their canonical
findings. Use them only to:

1. **Calibrate** your detection threshold — what counts as Long Method,
   Feature Envy, etc., in real C++ code.
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

- `language`:   cpp
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```cpp
{SOURCE_CODE}
```

Respond with the JSON object only — do not reference the exemplars in your
output.
