---
title: "Asynchrony"
author: Maxim Menshikov
layout: defect
permalink: /js/async
group:
   - js
---

Defects in asynchronous control flow, where a promise's outcome is never observed. When a rejection has no `catch` or `await` to receive it, the failure is swallowed or escalates to an unhandled-rejection event — either way the program continues as if the operation succeeded, losing errors and leaving state half-updated.
