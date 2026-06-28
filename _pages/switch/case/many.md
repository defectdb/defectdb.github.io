---
title: "Too many switch cases"
author: Maxim Menshikov
layout: defect
permalink: /switch/case/many
arch:
   - native
vulnerability:
   - None
ddos:
   - Low
group_full: switch.case
group:
   - switch
   - case
---
Too many switch cases might lead to performance degradation

# Impact

A single `switch` carries a very large number of cases. Beyond a point this hurts
both maintainability and performance. The function becomes a monolith that is hard
to read, test, and modify; adding a new variant means editing one ever-growing
block, and it is easy to misplace a `break` or duplicate a label. Depending on how
the values are distributed, a huge `switch` may also compile to something slower
than expected — a chain of comparisons or a multi-level search rather than a single
jump table — adding avoidable dispatch cost on a hot path.

It is a structural/quality defect: the program still computes the right answer, but
the design does not scale and the dispatch can be needlessly slow.

# Vulnerability potential

No direct security relevance: the number of cases does not by itself enable memory
corruption or any trust-boundary violation, so the vulnerability rating is `None`.
The only marginal concern is performance — a large, poorly-lowered `switch` on a
hot path adds latency that, under heavy load, contributes slightly to slowdowns —
hence a `Low` DoS rating.

# Technical details

## Dispatch lowering
For a dense, contiguous range of integer labels the compiler emits a jump table:
one indexed branch, O(1). When labels are sparse or the value range is wide, the
table would be huge, so the compiler falls back to a balanced comparison tree
(O(log n)) or a linear `if`/`else` chain (O(n)) — so "many cases" with scattered
values can mean noticeably slower dispatch than the table form. Very large tables
also cost instruction-cache footprint.

## Maintainability
A switch with dozens of cases concentrates unrelated handling in one function,
inflating cyclomatic complexity and making review and testing harder. It commonly
indicates a missing abstraction: the variants want to be data (a table) or types
(polymorphism), not hand-written labels.

## Better structures
- A lookup table mapping key → handler (`Handler table[N]` indexed by the value,
  or `std::unordered_map<Key, Handler>` for sparse keys) gives O(1) dispatch and
  splits the bodies into small functions.
- In C++, virtual dispatch / a registry of handlers replaces the `switch` when the
  cases correspond to types.

# Catching the issue

## Static analysis / metrics
The analyzer emitting this diagnostic flags a `switch` whose case count exceeds a
threshold. SonarQube, clang-tidy, Cppcheck and similar report the high cyclomatic
complexity and function length that large switches create.

## Refactor patterns
Replace the giant `switch` with a dispatch table or polymorphism; move each case's
work into its own named handler. This keeps dispatch fast (table lookup) and the
code modular.

## Review rule
Treat a `switch` growing past a couple dozen cases as a signal to introduce a
table- or type-driven design rather than adding another label.

# How to reproduce

Compile with `-O2 -S` and compare: a `switch` over sparse values lowers to a
comparison tree / chain rather than a single jump table, which a table-based
dispatch would avoid. Observe the branchy generated code.

```c
#include <stdio.h>

const char *name(int code)
{
    switch (code) {           /* sparse values: no dense jump table */
    case 1:    return "alpha";
    case 7:    return "bravo";
    case 42:   return "charlie";
    case 113:  return "delta";
    case 256:  return "echo";
    case 1000: return "foxtrot";
    case 4096: return "golf";
    case 9001: return "hotel";
    /* ... dozens more scattered labels ... */
    default:   return "unknown";
    }
}

int main(void) { printf("%s\n", name(4096)); return 0; }
```
