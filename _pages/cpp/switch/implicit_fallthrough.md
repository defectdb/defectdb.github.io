---
title: "Switch case falls through"
author: Maxim Menshikov
layout: defect
permalink: /cpp/switch/implicit_fallthrough
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: cpp.switch
group:
   - cpp
   - switch
---
Case body executes statements but does not terminate (break / return / throw / [[fallthrough]]); execution silently drops into the next case

# Impact

After a `case` label's statements run, control continues into the next label's
statements unless it is explicitly stopped. When a `break` (or `return`,
`throw`, `goto`, `[[fallthrough]]`) is forgotten, the matched case executes and
then keeps going into one or more subsequent cases. The program performs extra,
unintended work: state is mutated twice, the wrong branch's side effects fire,
or a "default" handler runs on top of a real case. These are logic bugs that
typically surface as wrong results or corrupted state rather than crashes, and
they are easy to miss in review because the control flow looks structured.

# Vulnerability potential

Mostly a correctness defect with no inherent memory-safety angle.

1. If the fallen-into case performs a security-relevant action — granting a
   permission, skipping a validation step, selecting a weaker code path — the
   accidental execution can become an authorization or validation flaw. This is
   entirely dependent on what the next case does.

Absent such a case, this is a logic error with no direct security consequence;
it neither corrupts memory nor consumes unbounded resources.

# Technical details

`switch` in C and C++ is structurally a computed `goto` into a block of
labeled statements; labels do not introduce scopes that stop execution.
"Falling through" is therefore the default behavior, deliberately retained from
C for cases like grouping labels (`case 'a': case 'b':`) where it is wanted.

## Intentional vs accidental

The language cannot tell an intended fall-through from a forgotten `break`.
C++17 added the `[[fallthrough]]` attribute precisely to let the programmer
mark the intentional cases, so tools can warn on every unmarked one. An empty
case that immediately stacks onto the next label (no statements between the two
labels) is not a fall-through and is not flagged.

## Scope of a missing break

Without a terminator, execution runs through *every* following case body until
it hits a `break` or the end of the switch — not just the one immediately
after — so a single missing `break` can run several cases.

# Catching the issue

## Compiler

GCC and Clang implement `-Wimplicit-fallthrough`; with `-Werror` it forces
every non-trivial fall-through to be either fixed or annotated with
`[[fallthrough]]`. MSVC offers `/we26819` via the analysis ruleset.

## Static analysis

clang-tidy `bugprone-switch-missing-default-case` and the misc fall-through
checks, plus PVS-Studio V796 and Coverity, detect the pattern. The Core
Guidelines (ES.78) require explicit termination of every non-empty case.

## Style

Always end each case with `break`/`return`/`throw`, and use `[[fallthrough]];`
when fall-through is genuinely intended so the warning stays clean.

# How to reproduce

Compile with `-Wimplicit-fallthrough -Werror` and it refuses to build; run as-is
and `classify(2)` prints both "even" and "small" because of the missing break.

```cpp
#include <iostream>

void classify(int x) {
    switch (x) {
        case 2:
            std::cout << "even\n";
            // BUG: no break here
        case 1:
            std::cout << "small\n";
            break;
        default:
            std::cout << "other\n";
    }
}

int main() {
    classify(2);   // prints "even" AND "small"
}
```
