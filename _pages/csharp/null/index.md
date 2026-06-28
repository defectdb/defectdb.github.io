---
title: "Null handling"
author: Maxim Menshikov
layout: defect
permalink: /csharp/null
group:
   - csharp
---

Defects in code that handles the absence of a value, where a `null` reaches an operation that assumes a live object. The failure is the familiar `NullReferenceException`, but the root cause is a contract about nullability that one side did not honor.

A representative case is calling an instance `Equals(null)` on a receiver that is itself null: the comparison throws before it can answer, where the static `object.Equals` or a null-tolerant pattern would have returned a clean result.

