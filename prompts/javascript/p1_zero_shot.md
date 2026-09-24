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

Detect every code smell in the JavaScript source file below. Apply the
taxonomy and the output schema exactly. Emit JSON only.

## Input

- `language`:   javascript
- `file_path`:  `{FILE_PATH}`
- `class_name`: `{CLASS_NAME}`

```javascript
{SOURCE_CODE}
```

Respond with the JSON object only.
