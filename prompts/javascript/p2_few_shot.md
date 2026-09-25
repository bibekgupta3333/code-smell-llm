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

<!-- USER -->
## Task

Detect every code smell in the JavaScript source file below. The worked
examples below illustrate the **format and decision threshold**: copy their
structure, do not copy their findings. Note that one example deliberately
shows clean code with `findings: []` — emit `[]` when uncertain.

## Worked examples (JavaScript)

{FEW_SHOT_EXAMPLES}

## Now analyse this file

- `language`:   javascript
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```javascript
{SOURCE_CODE}
```

Respond with the JSON object only.
