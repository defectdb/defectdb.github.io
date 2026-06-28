---
title: "with statement"
author: Maxim Menshikov
layout: defect
permalink: /js/legacy/with
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: js.legacy
group:
   - js
   - legacy
---
with is forbidden in strict mode and makes name resolution ambiguous

# Impact

The `with (obj) { ... }` statement adds `obj` to the front of the scope chain for
its block, so a bare name inside the block might refer to a property of `obj`,
or to an outer variable, or be a new global — and which one cannot be decided
until run time, on each entry, because the property set of `obj` can change. This
makes the code unreadable to humans and to tooling, defeats the engine's
scope-based optimisations (everything inside must be resolved dynamically), and
produces surprising bugs: assigning to a name that is *not* a property of `obj`
silently writes to an outer scope or creates a global instead. Because `with` is
a `SyntaxError` in strict mode and in ES modules, code using it cannot be moved
into those contexts without rewriting.

# Vulnerability potential

`with` has little direct security relevance. The realistic concern is indirect:
its ambiguous name resolution makes it easy to write a statement that the author
believes touches a property of `obj` but that actually reads or writes an outer
variable or a global, and such a silent mis-binding could corrupt state used in
a security decision. There is also a minor information-confusion angle when
`obj` is attacker-influenced, since the attacker controls which names resolve as
properties — but this only affects code already structured around `with`. These
are correctness risks rather than an injection or memory-safety vulnerability, so
the rating is Low.

# Technical details

A `with` statement creates an *object environment record* whose binding object is
the evaluated expression and pushes it onto the running execution context's
lexical environment for the duration of the block. Every identifier lookup in the
block first does a `HasProperty` check against that object (walking its prototype
chain) before falling through to the enclosing scopes. Because the object's
properties — including inherited ones — can change between iterations, the
binding of a given name is genuinely dynamic.

## Why engines deoptimise it

Optimising compilers resolve variable references to fixed slots at compile time.
`with` makes that impossible: any name could be shadowed by a property, so the
engine must fall back to dynamic lookups for the whole block, which is slow and
blocks inlining.

## Strict mode

In strict-mode code, ES modules, and class bodies, `with` is a `SyntaxError` —
the language committee removed it from the "safe" subset. This is the practical
reason it must be eliminated when modernising code.

## Replacements

Use a `const` alias (`const o = obj;` then `o.x`), destructuring
(`const { x, y } = obj;`), or just repeat the receiver. All are statically
analysable and optimiser-friendly.

# Catching the issue

## Linters

ESLint's `no-with` rule (on by default in `eslint:recommended`) flags every
`with` statement. Biome and most style guides forbid it outright.

## Use strict mode

Adding `"use strict"` to a script, or converting it to an ES module, turns any
`with` into a hard `SyntaxError` at parse time, so the compiler itself becomes
the detector. TypeScript likewise rejects `with` in strict/module code.

## Review

Treat any `with` as a defect and replace it with a `const` alias or
destructuring. There is no configuration in which `with` is the right tool.

# How to reproduce

Observe that the assignment inside `with` does not land on `obj` but escapes to
an outer variable, because `obj` has no own `count` property.

```js
let count = 0;
const obj = { value: 10 };

with (obj) {
  value = 20;   // sets obj.value (obj has it)
  count = 99;   // obj has no `count` -> writes the OUTER count!
}

console.log(obj.value); // 20
console.log(count);     // 99  (surprise: outer variable clobbered)

// `with` itself is a SyntaxError under "use strict"
```

