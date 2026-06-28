---
title: "Non-trivial switch case might cause performance issues"
author: Maxim Menshikov
layout: defect
permalink: /switch/case/non_trivial
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
Non-trivial switch case might cause performance issues

# Impact

A `switch` case contains a substantial amount of inline logic rather than a short
action or a delegation to a function. Several problems follow. The case is hard to
read and review, so bugs (a missing `break`, a misplaced variable declaration)
hide easily. The body bloats the enclosing function, hurting instruction-cache
behaviour and inlining decisions. And when many cases each carry heavy logic, the
compiler is less able to lower the `switch` to an efficient jump table, so dispatch
degrades toward a chain of comparisons.

This is mainly a maintainability and micro-performance defect; it does not change
what the program computes, only how clearly and how fast it does it.

# Vulnerability potential

There is no direct security exposure: the size of a case body neither corrupts
memory nor crosses a trust boundary. The vulnerability rating is `None`. The only
marginal concern is performance — heavy, poorly-dispatched cases on a hot path add
latency, which under extreme load contributes slightly to slowdowns — giving a
`Low` DoS rating. Note that the classic `switch` security pitfall (a fall-through
from a missing `break`) is a *separate* defect; this one is about case complexity.

# Technical details

## How switch is compiled
For dense, simple integer cases a compiler emits a jump table — O(1) dispatch. For
sparse values it may emit a binary search or a balanced comparison tree. Large or
side-effect-heavy case bodies increase the function's size and register pressure,
which can push the compiler away from the table form and inhibit inlining of the
whole function.

## Why "non-trivial" matters
A case that declares locals, loops, allocates, or runs multi-step logic:
- obscures control flow and makes accidental fall-through easy to miss;
- duplicates logic that ought to be shared across cases;
- couples unrelated concerns inside one large function, raising cyclomatic
  complexity and the cost of every future change.

## The cleaner shape
Each case should perform a short action or call a well-named handler
(`case X: return handle_x(ctx);`). A table of function pointers / a
`std::unordered_map<Key, Handler>`, or in C++ polymorphic dispatch, replaces a
sprawling `switch` entirely and keeps dispatch fast and the bodies small.

# Catching the issue

## Static analysis / metrics
The analyzer emitting this diagnostic flags cases whose body exceeds a complexity
or size threshold. clang-tidy, Cppcheck, SonarQube and similar tools report high
per-function cyclomatic complexity and overlong functions that large cases
produce.

## Refactor patterns
Extract each non-trivial case into its own function; replace the `switch` with a
dispatch table or polymorphism when there are many handlers. Keep case bodies to a
handful of lines.

## Review rule
Treat any case body longer than a few statements, or one that declares its own
locals/loops, as a candidate for extraction during review.

# How to reproduce

Compile and inspect the generated assembly (`-O2 -S`): the heavy, branch-laden
case bodies keep the compiler from emitting a clean jump table and bloat the
function compared with the same logic moved into separate handlers.

```c
#include <stdio.h>

int dispatch(int op, int *data, int n)
{
    switch (op) {
    case 0: {
        /* Non-trivial body: loops, locals, multi-step logic inline. */
        long sum = 0;
        for (int i = 0; i < n; ++i)
            sum += (data[i] * 31 + 7) ^ (data[i] >> 2);
        for (int i = 0; i < n; ++i)
            if (data[i] < 0) sum -= data[i];
        return (int)(sum % 1000003);
    }
    /* ... several more equally heavy cases ... */
    default:
        return -1;
    }
}

int main(void) { int d[] = {1,2,3}; printf("%d\n", dispatch(0, d, 3)); }
```
