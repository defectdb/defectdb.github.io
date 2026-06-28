---
title: "Debugging"
author: Maxim Menshikov
layout: defect
permalink: /rust/debug
group:
   - rust
---

Debugging scaffolding left behind in committed code. The `dbg!` macro is meant for momentary inspection during development; when it survives into a merged change it writes to standard error on every call, leaks values and file-line locations into output, and quietly signals that a diagnostic session was never cleaned up.
