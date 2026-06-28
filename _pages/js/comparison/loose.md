---
title: "Loose equality (== or !=)"
author: Maxim Menshikov
layout: defect
permalink: /js/comparison/loose
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: js.comparison
group:
   - js
   - comparison
---
Loose equality performs type coercion; use === and !== for predictable comparison

# Impact

Loose equality (`==`/`!=`) coerces its operands before comparing, so values of
different types can test equal in ways that rarely match the author's intent.
`0 == ""`, `0 == "0"`, `0 == false`, `"" == false`, `null == undefined`,
`[] == ""`, `[] == 0` and `"0e0" == 0` all evaluate to `true`, while
`NaN != NaN`. Code that relies on `==` for validation, branching or
de-duplication therefore takes the wrong branch for specific inputs: a guard
such as `if (input == 0)` also accepts `""`, `"0"`, `false` and `[]`; a check
like `if (count == "")` is true when `count` is `0`. Because the failures are
data-dependent, they slip through testing and surface only for the particular
values that happen to coerce.

# Vulnerability potential

The security relevance is low but not zero.

1. Coercion inside a security decision can flip it. A guard such as
   `if (input == 0)` or `if (flag == true)` where one operand is
   attacker-influenced can be satisfied by an unexpected type — an empty
   string, `"0"`, `false` or `[]` — letting a check pass that the author
   expected to fail.
2. Allow/deny membership tests written with `==` become inconsistent when an
   attacker supplies a value that coerces to a permitted one, so an entry can
   match in one comparison and not in another.

Exploitation requires the loose comparison to drive an authorization or
filtering decision and the attacker to control one side, so the window is
narrow — but such code does occur in validation layers.

# Technical details

`==` runs the Abstract Equality Comparison algorithm (ECMAScript spec
`IsLooselyEqual`), `===` runs Strict Equality (`IsStrictlyEqual`). When the
two operands have different types, the abstract algorithm coerces them:
`undefined` and `null` are mutually equal and equal to nothing else;
a number compared with a string converts the string to a number; a boolean is
converted to a number first (`true` -> `1`, `false` -> `0`); and an object
compared with a primitive is converted with `ToPrimitive`. Strict equality does
none of this and returns `false` immediately on a type mismatch.

## Object coercion runs user code

`ToPrimitive` calls `Symbol.toPrimitive`, then `valueOf`, then `toString` on the
object. A comparison like `obj == 1` can therefore execute arbitrary code on an
attacker-supplied object, with side effects and a controllable result — an extra
reason to avoid `==` on untrusted values.

## NaN and signed zero

`NaN` is not equal to anything, including itself, under both `==` and `===`, so
`x == NaN` is always false; use `Number.isNaN(x)`. `+0 == -0` and `+0 === -0`
are both true; only `Object.is` distinguishes them.

# Catching the issue

## Linters

ESLint's `eqeqeq` rule flags every `==`/`!=` and is autofixable; the common
configuration `["error", "always", { "null": "ignore" }]` still permits the
deliberate `x == null` idiom (a single check for both `null` and `undefined`)
while rejecting all other loose comparisons. The `no-eq-null` rule covers the
remaining case if you want it forbidden too.

## Type checkers

TypeScript does not ban `==`, but with strict settings it rejects comparisons
between provably incompatible types, removing a class of these bugs. Biome's
`noDoubleEquals` and most style guides (Airbnb, Google) require `===`.

## Review

Treat any `==`/`!=` as a defect unless it is the intentional `x == null`
shorthand, and prefer writing that as `x === null || x === undefined` or `x ==
null` with an explanatory comment.

# How to reproduce

Observe that loose equality reports surprising matches that strict equality
rejects.

```js
console.log(0 == "");      // true
console.log(0 == "0");     // true
console.log("" == "0");    // false  -> == is not transitive!
console.log([] == 0);      // true
console.log([] == "");     // true
console.log(null == undefined); // true

console.log(0 === "");     // false
console.log([] === 0);     // false

// coercion can run attacker code:
const evil = { valueOf() { console.log("side effect!"); return 0; } };
console.log(evil == 0);    // logs "side effect!", then true
```

