---
title: "Asynchrony"
author: Maxim Menshikov
layout: defect
permalink: /csharp/async
group:
   - csharp
---

Defects in how methods are declared and composed with `async`/`await`, where the asynchronous control flow escapes the caller's ability to observe it. The signature looks ordinary, but the returned `Task` — or the absence of one — changes who is responsible for the work and its failures.

The dominant case is the `async void` method: it returns no awaitable, so the caller cannot await completion or catch what it throws, and an exception is re-raised on the synchronization context where it typically tears down the process. Outside event handlers, an `async Task` return is almost always the correct shape.

