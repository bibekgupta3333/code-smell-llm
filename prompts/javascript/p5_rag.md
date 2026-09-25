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

## Retrieval policy

The user message contains *retrieved exemplars*: top-k similar smelly
JavaScript snippets from the training corpus, each with their canonical
findings. Use them only to:

1. **Calibrate** your detection threshold — what counts as Long Method,
   Feature Envy, etc., in real JavaScript code.
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

- `language`:   javascript
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```javascript
{SOURCE_CODE}
```

Respond with the JSON object only — do not reference the exemplars in your
output.
