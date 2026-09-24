"""Verify all 20 prompt files have proper structure for research evaluation."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CANON_SMELLS = {
    'Long Method', 'Large Class', 'Primitive Obsession', 'Long Parameter List',
    'Data Clumps', 'Switch Statements', 'Temporary Field', 'Refused Bequest',
    'Alternative Classes with Different Interfaces',
    'Parallel Inheritance Hierarchies', 'Divergent Change', 'Shotgun Surgery',
    'Comments', 'Duplicate Code', 'Lazy Class', 'Data Class', 'Dead Code',
    'Speculative Generality', 'Feature Envy', 'Inappropriate Intimacy',
    'Message Chains', 'Middle Man', 'Control Coupling',
}

REQUIRED_RUNTIME_PLACEHOLDERS = {'{TAXONOMY}', '{OUTPUT_SCHEMA}', '{SYSTEM_BLOCK}',
                                  '{FILE_PATH}', '{CLASS_NAME}', '{SOURCE_CODE}'}
PER_STRATEGY_PLACEHOLDERS = {
    'p2_few_shot.md':       {'{FEW_SHOT_EXAMPLES}'},
    'p5_rag.md':            {'{RETRIEVED_SNIPPETS}'},
}

def main() -> int:
    fails = 0
    for f in sorted(ROOT.glob('*/*.md')):
        t = f.read_text()
        problems = []
        if '<!-- SYSTEM -->' not in t: problems.append('no SYSTEM marker')
        if '<!-- USER -->'   not in t: problems.append('no USER marker')
        for ph in REQUIRED_RUNTIME_PLACEHOLDERS:
            if ph not in t: problems.append(f'missing {ph}')
        for ph in PER_STRATEGY_PLACEHOLDERS.get(f.name, set()):
            if ph not in t: problems.append(f'missing {ph}')
        if f.name == 'p3_taxonomy_tree.md':
            missing = sorted(s for s in CANON_SMELLS if s not in t)
            if missing: problems.append(f'P3 missing smells: {missing}')
        if f.name == 'p4_self_verify.md':
            for tag in ('<analysis>', '</analysis>', '<answer>', '</answer>'):
                if tag not in t: problems.append(f'missing {tag}')
        status = 'OK' if not problems else 'FAIL: ' + '; '.join(problems)
        print(f'{f.parent.name:11s} {f.name:25s} {status}')
        if problems: fails += 1
    print(f'\n{fails} file(s) failed' if fails else '\nAll prompts OK')
    return fails

if __name__ == '__main__':
    raise SystemExit(main())
