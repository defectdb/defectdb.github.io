---
title: "non-null assertion"
author: Maxim Menshikov
layout: defect
permalink: /ts/type/non_null_assertion
arch:
   - native
vulnerability:
   - Low
ddos:
   - Low
group_full: ts.type
group:
   - ts
   - type
---
x! overrides the TypeScript null check; prefer an explicit null guard or a runtime check

# Impact

The postfix `!` (non-null assertion) tells the compiler "trust me, this value is
not `null` or `undefined` here" and removes `null`/`undefined` from the
expression's type — *without emitting any runtime check*. It is a pure
compile-time claim. When the claim is wrong, nothing stops execution at the `!`;
the program proceeds with a value the type system now believes is non-null, and
the failure surfaces later as a `TypeError: Cannot read properties of undefined`
(or `null`) at the first property access or call. In other words `!` does not
make the value safe, it makes the compiler stop warning you — so it converts a
checkable compile-time error into an unchecked runtime crash, often at a point
removed from the bad assertion, which makes it harder to trace.

# Vulnerability potential

The non-null assertion is mainly a correctness and availability issue rather than
an exploitable hole.

1. **Denial of service via crashes.** A wrong `!` on a value an attacker can make
   `null`/`undefined` — a missing query parameter, an absent map entry, an empty
   query result — throws an uncaught `TypeError`. On a Node server that can
   terminate the process or abort the request path on demand, which is why the
   DDoS rating is Low.
2. **Suppressed guard.** `!` silences the very check that would have forced the
   developer to handle the empty case, so a missing-data branch that should have
   been validated is skipped. If that branch guarded a security decision, the
   skip is a logic weakness.

It does not grant code execution or memory unsafety, so the vulnerability rating
is Low; the realistic harm is crashes and unhandled edge cases.

# Technical details

Under `strictNullChecks`, `null` and `undefined` are distinct types that must be
removed from a union before the value is used as the non-nullable type. The `!`
operator does this removal in the type system only; it emits **no** JavaScript —
`x!.foo` compiles to exactly `x.foo`. So the assertion is sound only if the
runtime really matches the claim, and the compiler cannot verify that.

## When `!` is tempting but wrong

Common misuses: `document.getElementById(id)!` (the element may not exist),
`map.get(key)!` (the key may be absent), `arr.find(pred)!` (no match returns
`undefined`), and a class field initialised in a lifecycle hook rather than the
constructor. Each can legitimately be nullish at run time.

## Safer alternatives

Narrow with an explicit guard (`if (x == null) throw ...` / early return),
optional chaining (`x?.foo`) when "do nothing if absent" is acceptable, or
nullish coalescing (`x ?? fallback`) to supply a default. For class fields that
really are assigned before use, the *definite assignment* form `field!: T` is a
narrower, more honest tool than scattering `!` at every use site.

## Distinguish the operators

`x!` is the non-null assertion (postfix). `x as T` is a type assertion (cast).
Both bypass checks; both are worth scrutiny, but they do different things.

# Catching the issue

## Linters

`@typescript-eslint/no-non-null-assertion` flags every postfix `!`. Many teams
set it to `warn` (since some uses are pragmatic) or `error` with targeted
`eslint-disable` comments that document why each surviving `!` is safe.
`no-non-null-asserted-optional-chain` specifically bans the dangerous
`x?.y!` pattern.

## Compiler

`strictNullChecks` (part of `strict`) is what makes the nullable types visible in
the first place; without it `!` is pointless and crashes are unguarded anyway, so
keep it on. The compiler will not reject a `!`, so the lint rule is the real
gate.

## Review and runtime

Treat each `!` as an unverified assumption: prefer a real guard, and if the value
truly cannot be null, prove it with a check or assertion function (`assert(x)`)
that throws a clear error at the point of the bad assumption instead of a vague
`TypeError` later.

# How to reproduce

Observe that the `!` version type-checks but throws at run time when the lookup
misses; the guarded version is rejected by neither the compiler nor reality.

```ts
const users = new Map<string, { name: string }>([
  ["alice", { name: "Alice" }],
]);

// `!` asserts non-null; compiles fine, crashes for a missing key
function greetUnsafe(id: string): string {
  return users.get(id)!.name; // TypeError if id is absent
}
// greetUnsafe("bob") -> throws: Cannot read properties of undefined

// guarded: the compiler forces you to handle the empty case
function greetSafe(id: string): string {
  const user = users.get(id);
  if (!user) throw new Error(`unknown user: ${id}`);
  return user.name;
}
```

