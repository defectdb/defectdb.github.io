---
title: "setTimeout/setInterval called with string"
author: Maxim Menshikov
layout: defect
permalink: /js/security/settimeout_string
arch:
   - native
vulnerability:
   - High
ddos:
   - Low
group_full: js.security
group:
   - js
   - security
---
Passing a string to setTimeout/setInterval invokes eval semantics on the argument; pass a function instead

# Impact

When `setTimeout` or `setInterval` is given a string as its first argument, the
host compiles and runs that string as JavaScript when the timer fires, exactly
as `eval` would. So `setTimeout("doWork()", 100)` is not scheduling a reference
to `doWork`; it is scheduling a deferred `eval` of the text `"doWork()"`. If any
part of that text comes from input the program does not fully control, the timer
becomes a code-injection sink that runs attacker code with the page's or
process's full privileges. Even when the string is a constant, this form is
slower (the engine recompiles on every call, badly hurting `setInterval`),
breaks minification and dead-code elimination, evaluates in global scope so it
cannot see local variables, and silently does nothing useful if a referenced
name was renamed.

# Vulnerability potential

The string form is "implied eval" and carries the same code-injection risk
(CWE-95) as `eval` itself.

1. **Remote code execution / XSS.** Any attacker-influenced substring in the
   timer string is executed as JavaScript. In the browser this runs in the
   page's origin (reads cookies, tokens, DOM, exfiltrates data); in Node it can
   reach `require`, `child_process`, the filesystem and the network.
2. **Privilege inheritance.** The code runs with the privileges of the realm,
   and because the string form always evaluates in *global* scope, injected code
   has direct access to global APIs.
3. **String-concatenation traps.** The danger is most common when a string is
   built up — `setTimeout("show('" + name + "')", 0)` — where `name` breaks out
   of the quotes. This pattern is easy to introduce and easy to overlook.
4. **Denial of service.** A controlled string can schedule `while(true){}` or an
   allocation bomb on the single event loop, hanging the tab or process — hence
   the Low DDoS rating, amplified by `setInterval` repeating it.

As with `eval`, sanitising the string is not a reliable defence; pass a function
instead.

# Technical details

`setTimeout`/`setInterval` are defined by the HTML standard (and Node's timers).
Their first parameter is typed as a `Function` *or* a string; when a string is
passed, the algorithm compiles it with the equivalent of the indirect-`eval`
machinery and runs it in global scope at the scheduled time. This is a
deliberate legacy affordance kept for backward compatibility, not a feature to
use.

## Pass a function, not a string

The correct form passes a callable: `setTimeout(doWork, 100)` or
`setTimeout(() => show(name), 0)`. A closure captures `name` by value and never
re-parses it as code, eliminating both the injection risk and the recompilation
cost. Extra timer arguments are forwarded to the callback:
`setTimeout(show, 0, name)` also works.

## Related sinks

This is the same family of defect as `eval` and `new Function("...")`. The
`Function` constructor likewise compiles a string, and like the string timer it
evaluates in global scope.

## CSP and Node flags

A Content-Security-Policy without `'unsafe-eval'` makes the *string* form of
`setTimeout`/`setInterval` throw in the browser (the function form keeps
working). Node's `--disallow-code-generation-from-strings` has the analogous
effect server-side.

# Catching the issue

## Linters and static analysis

ESLint's `no-implied-eval` is purpose-built for this: it flags a string passed to
`setTimeout`, `setInterval`, `setImmediate` and `execScript`, as well as
`new Function`. Security scanners (Semgrep, CodeQL `js/code-injection`,
SonarQube, `eslint-plugin-security`) trace tainted input into these sinks.

## Runtime / deployment

Ship a CSP without `'unsafe-eval'` in the browser, and run Node with
`--disallow-code-generation-from-strings`, so any string-form timer throws
instead of executing.

## Review rule

A string first argument to `setTimeout`/`setInterval` is always a defect —
replace it with a function reference or arrow function, even when the string is
a literal, since the function form is faster and minifier-safe as well as
secure.

# How to reproduce

Observe that the string built from input is executed as code, while the function
form treats the same input as data.

```js
// pretend `name` came from a query string: name = "');globalThis.pwned=true;//"
const name = "');globalThis.pwned=true;//";

// string form: re-parsed as code, the payload breaks out
setTimeout("greet('" + name + "')", 0);
setTimeout(() => console.log(globalThis.pwned), 10); // true

// function form: `name` stays a string, nothing is injected
setTimeout(() => greet(name), 0);
function greet(n) { console.log("hi", n); }
```

