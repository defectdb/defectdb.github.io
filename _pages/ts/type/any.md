---
title: "any type used"
author: Maxim Menshikov
layout: defect
permalink: /ts/type/any
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: ts.type
group:
   - ts
   - type
---
any disables TypeScript's checks for this binding; prefer a precise type, unknown, or a generic

# Impact

`any` is TypeScript's escape hatch: a value typed `any` is exempt from all static
checking. You can read any property, call it, index it, pass it anywhere and
assign anything to it, and the compiler stays silent. The defect is that this
silence is *contagious* — `any` flows outward. Accessing a property of an `any`
yields `any`, the return of a function typed to return `any` is `any`, so a
single `any` at an API boundary erases the types of everything downstream that
touches it. The cost is the loss of exactly the guarantees TypeScript exists to
provide: typos, wrong argument counts, calls on `undefined`, and shape
mismatches that would have been compile errors instead surface as runtime
`TypeError`s in production, and editor autocomplete/refactoring quietly stops
working on the affected values.

# Vulnerability potential

`any` is a type-safety defect, not a direct vulnerability, but it has a real if
secondary security effect: it removes the compiler's ability to enforce the
shape and type of data, and that often matters most exactly where untrusted
input enters.

1. **Unvalidated input flows unchecked.** A request body or parsed JSON typed as
   `any` can be passed straight into queries, filesystem paths, or HTML without
   the type system signalling that its shape was never verified, masking missing
   validation that could enable injection or path traversal.
2. **Eroded invariants.** Type confusion introduced by `any` (a number where a
   string was expected, a missing field assumed present) can cause logic to take
   an unintended branch, including in authorization code.

These are indirect, so the rating is Low — `any` does not create a hole by
itself, it removes a guard rail that would have helped catch one.

# Technical details

`any` is the type that is assignable *to* and *from* every other type, and which
disables property/call/index checking on its values. This bidirectional
assignability is what makes it spread: assign an `any` into a typed variable and
the unsoundness travels with it, with no cast and no warning.

## any vs unknown

`unknown` is the type-safe counterpart. It also holds any value, but you can do
nothing with an `unknown` until you *narrow* it (via `typeof`, `instanceof`, a
discriminant check, or a type guard). So `unknown` forces validation where `any`
skips it; prefer `unknown` for genuinely dynamic data (JSON, `catch` bindings,
external APIs) and narrow before use.

## Where any sneaks in

It often arrives implicitly: an untyped function parameter, a `JSON.parse`
result (typed `any`), `catch (e)` before TS 4.4 (now `unknown` under
`useUnknownInCatchVariables`), and untyped third-party modules. These implicit
`any`s are the ones most worth eliminating.

## Better alternatives

Use a precise interface/type, a union, or `generics` to keep a relationship
between input and output types (`function first<T>(xs: T[]): T`) instead of
`any[] -> any`.

# Catching the issue

## Compiler

Enable `strict` (which turns on `noImplicitAny`) so the compiler errors on any
parameter or variable whose type would silently become `any`. Add
`useUnknownInCatchVariables` (on under `strict`) so `catch` bindings are
`unknown`, not `any`.

## Linters

`@typescript-eslint` provides a battery of rules: `no-explicit-any` (ban the
keyword), and the `no-unsafe-*` family (`no-unsafe-assignment`,
`no-unsafe-member-access`, `no-unsafe-call`, `no-unsafe-argument`,
`no-unsafe-return`) which flag *uses* of an `any` value even when it arrived
implicitly from an untyped dependency — these catch what `noImplicitAny` cannot.

## Boundaries

At input boundaries, validate with a schema library (Zod, io-ts, valibot) that
parses `unknown`/external data into a precisely typed value, so `any` never
enters. In review, treat each `any` and each `as any` cast as needing a
justification.

# How to reproduce

Observe that the `any` version compiles cleanly yet throws at run time, while the
`unknown` version forces a check and is caught by the compiler.

```ts
function lengthOf(x: any): number {
  return x.length; // no error, even though x may have no `length`
}

lengthOf(42); // compiles; throws nothing but returns undefined-as-number nonsense
// (42).length is undefined -> returned as number, silent garbage

// safe alternative: unknown forces narrowing
function safeLength(x: unknown): number {
  if (typeof x === "string" || Array.isArray(x)) return x.length;
  throw new TypeError("no length");
}
// safeLength(42) -> compiler is happy, runtime throws a clear error
```

