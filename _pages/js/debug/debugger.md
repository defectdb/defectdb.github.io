---
title: "debugger statement"
author: Maxim Menshikov
layout: defect
permalink: /js/debug/debugger
arch:
   - native
vulnerability:
   - Low
ddos:
   - None
group_full: js.debug
group:
   - js
   - debug
---
debugger pauses execution under devtools and should be removed from shipped code

# Impact

The `debugger` statement is a programmatic breakpoint: when a debugger (such as
browser DevTools or the Node inspector) is attached, reaching the statement
halts execution there; with no debugger attached it is a no-op. Left in shipped
code it is dead weight at best, and a real annoyance at worst — anyone who opens
DevTools on the page (developers, QA, curious users, security researchers) has
their session frozen at that line, the UI stops responding, and it looks like
the application has hung. It signals unfinished work and erodes trust in the
build. The statement should never reach production; it belongs to an interactive
debugging session and should be removed before commit or stripped by the build.

# Vulnerability potential

`debugger` has essentially no offensive security relevance: it does not execute
attacker input, leak data, or corrupt state, and it only does anything when a
developer has voluntarily attached a debugger. The two minor notes are that it is
sometimes used *deliberately* in an infinite loop as an anti-analysis trick to
frustrate researchers inspecting a page (a nuisance, not a vulnerability of the
host application), and that its presence reveals the code was shipped without a
proper build/lint gate. Neither rises above Low.

# Technical details

`debugger` is a standard ECMAScript statement (the spec calls it the *Debugger
Statement*). Its defined behaviour is implementation-dependent: if a debugger is
present and active it should break, otherwise it has no observable effect. There
is no way to "trigger" it without an attached debugger, which is exactly why it
is harmless when no one is debugging and disruptive the moment someone is.

## Build-time handling

In practice it should never survive into a release bundle. Most bundlers strip it
automatically in production mode — Terser/UglifyJS remove `debugger` when the
`drop_debugger` compress option is on (the default), and esbuild/SWC drop it
under their minify settings. Relying on that is acceptable as a safety net, but
the statement should still not be committed.

## Distinguish from logging

Unlike a stray `console.log`, `debugger` actively pauses the program, so its
impact when it slips through is more visible and more disruptive than a leftover
log line.

# Catching the issue

## Linters

ESLint's `no-debugger` rule is in `eslint:recommended` and flags every
`debugger` statement; run it as an error in CI so a build fails rather than
ships the statement. Biome's `noDebugger` does the same.

## Build and CI

Enable `drop_debugger` (Terser) or the equivalent minify option so production
bundles are stripped even if one slips past review, and add a pre-commit hook or
CI grep as a backstop. Keep the lint rule as the primary gate so the issue is
caught at author time, not just removed silently at build time.

## Review

Treat any committed `debugger` as a defect; it has no place outside a live
debugging session.

# How to reproduce

Run this with DevTools or the Node inspector open (`node inspect file.js`) and
observe execution pausing at the `debugger` line; with no debugger attached it
runs straight through.

```js
function handleClick() {
  const value = compute();
  debugger; // execution halts here when DevTools is open
  return value;
}

function compute() { return 42; }
```

