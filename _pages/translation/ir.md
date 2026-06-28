---
title: "Failed to convert code to internal representation"
author: Maxim Menshikov
layout: defect
permalink: /translation/ir
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: translation
group:
   - translation
---
Failed to convert code to internal representation

# Impact

This is an analyzer-internal diagnostic. The source parsed successfully into an
AST, but the next stage — lowering that tree into Visao's intermediate
representation (IR) — could not complete. It is not a defect in the analyzed
program; it reports that the analyzer's own model of the code could not be built.

Because the analysis engine reasons over the IR (control-flow graphs, value
tracking, the defect checks), a function or translation unit that fails to lower
is **excluded from analysis**. Any real defects in that code are not reported, so
the file appears clean only because it was never modelled.

# Vulnerability potential

This message has essentially no security meaning for the analyzed code: it is a
limitation of the lowering stage, not an exploitable state in the target. The one
indirect risk is the familiar coverage gap — code that cannot be lowered is
skipped, so a genuine vulnerability there is missed. That keeps the rating at
`Low` rather than `None`. The diagnostic implies no memory corruption or other
unsafe behaviour inside Visao itself.

# Technical details

IR lowering walks the type-checked AST and rewrites each construct into a small,
uniform set of operations the analysis engine understands. The conversion fails
when it meets a construct it has no lowering rule for, or when an invariant the IR
builder relies on is violated.

## Unsupported constructs
Language or library features the lowering pass does not yet model — inline
assembly, computed `goto`, certain C++ features (coroutines, fold expressions,
complex template instantiations), compiler builtins, or vendor intrinsics. The
AST is valid but there is no rule to translate it.

## Incomplete semantic information
Lowering often needs resolved types and sizes. If a type is incomplete, a
`sizeof` is unresolved, or a symbol could not be linked to a declaration, the
builder cannot produce well-formed IR and aborts.

## Internal invariant violations
A node shape the builder did not anticipate (an unexpected combination of
qualifiers, an empty expression where one was required) can trip an assertion in
the lowering pass.

# Catching the issue

This is a tool diagnostic; the goal is to let lowering succeed, not to alter
program logic.

## Isolate the construct
The diagnostic points at the offending function or expression. Reduce it to a
minimal snippet that still fails; the failing construct is usually one specific
feature.

## Provide complete types
Make sure all needed headers and definitions are available so the front-end hands
complete, resolved types to the lowering stage; many failures are really missing
type information rather than a true gap.

## Report and gate
When standard, well-typed code fails to lower, file the minimal reproducer so a
lowering rule can be added. In CI, treat lowering failures as errors so the
resulting coverage gaps are not silently accepted.

# How to reproduce

Give the analyzer valid, parseable code that uses a construct the IR builder does
not model, such as inline assembly. The AST builds, but lowering reports a failure
to convert the function and the body is left unanalyzed.

```c
int probe_tsc(void)
{
    unsigned lo, hi;

    /* Parses fine, but the IR builder has no lowering rule for the
       inline-asm block and cannot model this function. */
    __asm__ volatile ("rdtsc" : "=a"(lo), "=d"(hi));

    return (int)lo;
}
```
