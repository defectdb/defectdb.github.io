---
title: "Variable shadows another variable"
author: Maxim Menshikov
layout: defect
permalink: /var/scope/shadowed
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: var.scope
group:
   - var
   - scope
---
Variable shadows outer level variable

# Impact

When an inner declaration reuses the name of a variable in an enclosing scope,
references in the inner block silently bind to the new variable instead of the
intended outer one. Code that *looks* like it updates the outer variable in fact
mutates a short-lived copy that is discarded at the end of the block, so the
outer state never changes. The result is a logic bug — a counter that stays at
zero, a flag that is never propagated, a result computed and thrown away — that
compiles cleanly and reads correctly at a glance.

# Vulnerability potential

Shadowing is primarily a correctness and readability defect with low direct
security relevance. The realistic risk is indirect: if the shadowed variable is a
security-relevant flag (an `authorized`, `is_admin`, or length/bounds value) and
an update meant for the outer scope is lost to the inner copy, a check can be
left at its default and a guard effectively bypassed. The vulnerability in such a
case lives in the lost update, with shadowing as the mechanism that hides it.

# Technical details

C and C++ permit an inner scope to declare a name that already exists in an outer
scope; name lookup resolves to the innermost declaration, hiding the outer one
for the rest of the block. This is legal and sometimes intentional, but it is a
frequent source of mistakes, especially when the shadowing declaration is added
during a later edit.

## Common forms
A loop or `if` block redeclaring a name from the function body; a local variable
with the same name as a parameter; a member variable shadowed by a local or
parameter in a method (so `x = v` writes the parameter, not `this->x`); and a
local that shadows a global. The accidental `int i;` inside a nested loop that
also has an outer `i` is a classic off-by-everything bug.

## Why it slips through
The program is well-formed, so without warnings enabled the compiler says
nothing. Reviewers reading the inner block in isolation see a plausible
assignment and do not notice it targets the wrong object.

# Catching the issue

## Compiler warnings
Enable `-Wshadow` on GCC/Clang (not part of `-Wall`); it reports a declaration
that hides one from an outer scope, including parameters and members
(`-Wshadow=local`, `-Wshadow-all`). On MSVC, `/W4` surfaces C4456–C4459 for the
shadowing cases. Build with `-Werror` to make them hard failures.

## Static analysis and conventions
clang-tidy's `bugprone-*` and readability checks, Cppcheck, and Coverity flag
shadowing. Conventions help too: prefer distinct names, mark members with a
trailing underscore or `this->`, and keep variable scopes small so collisions
are obvious.

# How to reproduce

Compile with `g++ -Wshadow`; the inner `count` shadows the outer one, so the
function always returns 0.

```cpp
#include <iostream>

int count_positive(const int *a, int n) {
    int count = 0;
    for (int i = 0; i < n; i++) {
        if (a[i] > 0) {
            int count = 1;   /* shadows the outer 'count' */
            (void)count;     /* the outer counter is never incremented */
        }
    }
    return count;            /* always 0 */
}

int main() {
    int data[] = {1, -2, 3};
    std::cout << count_positive(data, 3) << "\n";  /* prints 0, not 2 */
}
```
