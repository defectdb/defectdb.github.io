---
title: "var declaration"
author: Maxim Menshikov
layout: defect
permalink: /js/scope/var
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: js.scope
group:
   - js
   - scope
---
var is function-scoped and hoisted; prefer const for immutable bindings or let for mutable ones

# Impact

`var` is function-scoped, not block-scoped, and its declaration is hoisted to the
top of the enclosing function while its assignment stays in place. As a result a
`var` declared inside an `if`, `for` or `try` block leaks to the whole function,
reading it before the assignment yields `undefined` instead of a
`ReferenceError`, and re-declaring the same name silently succeeds. The classic
symptom is the loop-closure bug: every closure created in a `for (var i ...)`
loop captures the same single `i`, so they all observe its final value. These
are correctness defects — stale or shared values, accidental shadowing,
variables that appear "defined" before their initialiser — that produce wrong
output rather than a crash, and are easy to miss in review.

# Vulnerability potential

`var` has little direct security relevance: it is a scoping and style defect, not
a memory-safety or injection issue. The only indirect risk is that the
function-scope leak or a closure capturing the wrong value produces incorrect
logic in code that happens to make a security decision — for example a loop that
was meant to validate each item but ends up acting on the last one. That is a
correctness failure that could weaken a check, not a vulnerability introduced by
`var` itself, so the rating stays Low.

# Technical details

During the creation phase of a function's execution context the engine hoists
every `var` declaration and binds the name to `undefined`; the assignment runs
later when control reaches it. `let` and `const` are hoisted too but live in the
*temporal dead zone* until their declaration executes, so reading them early
throws a `ReferenceError` — the engine turns a silent bug into an error.

## Scope granularity

`var` ignores block boundaries; only functions (and the module/global scope)
create a `var` scope. `let`/`const` are block-scoped, so each `{ ... }`, loop
body and `catch` clause gets its own binding.

## Loop bindings

`for (let i = 0; ...)` creates a *fresh* binding of `i` for every iteration, so
a closure created in the body captures that iteration's value. `for (var i ...)`
has one binding shared by all iterations, which is why the closures all see the
final value. This is the single most common `var` bug.

## Redeclaration

Re-declaring with `var` in the same scope is allowed and silently merges, hiding
copy-paste mistakes; `let`/`const` raise a `SyntaxError` on redeclaration.

# Catching the issue

## Linters

ESLint's `no-var` rule flags every `var` and is autofixable to `let`/`const`;
pair it with `prefer-const` so bindings that are never reassigned become
`const`, and with `block-scoped-var` / `no-redeclare` if some `var` must remain.
`no-loop-func` catches the closure-in-loop pattern specifically.

## Type checkers and bundlers

TypeScript reports use-before-declaration for `let`/`const` thanks to the TDZ
and will surface the leaked-scope cases once `var` is removed. Most style guides
(Airbnb, Google, StandardJS) forbid `var` outright.

## Migration note

Mechanically replacing `var` with `let`/`const` is usually safe, but watch for
code that *relied* on function-scope leakage (a `var` used after its block);
those spots need the declaration hoisted to the right block manually.

# How to reproduce

Observe that all `var` closures print `3`, while `let` prints `0 1 2`, and that a
`var` is readable (as `undefined`) before its declaration.

```js
// hoisting: no error, prints undefined
console.log(hoisted); // undefined
var hoisted = 1;

// shared loop binding
const withVar = [];
for (var i = 0; i < 3; i++) withVar.push(() => i);
console.log(withVar.map((f) => f())); // [3, 3, 3]

const withLet = [];
for (let j = 0; j < 3; j++) withLet.push(() => j);
console.log(withLet.map((f) => f())); // [0, 1, 2]
```

