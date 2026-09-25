from __future__ import annotations

import re

CATEGORY_OF: dict[str, str] = {
    "Long Method": "Bloaters",
    "Large Class": "Bloaters",
    "Primitive Obsession": "Bloaters",
    "Long Parameter List": "Bloaters",
    "Data Clumps": "Bloaters",
    "Switch Statements": "Object-Orientation Abusers",
    "Temporary Field": "Object-Orientation Abusers",
    "Refused Bequest": "Object-Orientation Abusers",
    "Alternative Classes with Different Interfaces": "Object-Orientation Abusers",
    "Parallel Inheritance Hierarchies": "Object-Orientation Abusers",
    "Divergent Change": "Change Preventers",
    "Shotgun Surgery": "Change Preventers",
    "Comments": "Dispensables",
    "Duplicate Code": "Dispensables",
    "Lazy Class": "Dispensables",
    "Data Class": "Dispensables",
    "Dead Code": "Dispensables",
    "Speculative Generality": "Dispensables",
    "Feature Envy": "Couplers",
    "Inappropriate Intimacy": "Couplers",
    "Message Chains": "Couplers",
    "Middle Man": "Couplers",
    "Control Coupling": "Couplers",
}

SMELL_VOCAB: tuple[str, ...] = tuple(CATEGORY_OF)

ENTIRE_CLASS = "Entire Class"

LABEL_ALIASES: dict[str, str] = {
    "Message Chain": "Message Chains",
    "Switch Statement": "Switch Statements",
    "Temporary Fields": "Temporary Field",
    "Long Parameters List": "Long Parameter List",
    "Long Parameters": "Long Parameter List",
    "Parallel Inheritance Hierarchy": "Parallel Inheritance Hierarchies",
    "Parallel Inheritance": "Parallel Inheritance Hierarchies",
    "Middleman": "Middle Man",
    "Inappropriate Intimacies": "Inappropriate Intimacy",
    "Unnecessary Comments": "Comments",
    "Useless Comments": "Comments",
}

_LABEL_NAMES = sorted(set(CATEGORY_OF) | set(LABEL_ALIASES), key=lambda s: (-len(s), s))
LABEL_RE = re.compile(r"\b(" + "|".join(re.escape(n) for n in _LABEL_NAMES) + r")\b")
