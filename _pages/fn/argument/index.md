---
title: "Arguments"
author: Maxim Menshikov
layout: defect
permalink: /fn/argument
group:
   - fn
---

Defects in the values handed to a function and in how the call is resolved.
Passing a null where the callee dereferences it turns a routine call into a
crash, while overload sets that differ only in parameter order let a
transposed-argument call compile cleanly yet bind to the wrong function — both
cases deliver data the callee was never prepared to handle correctly.

