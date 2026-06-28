---
title: "Tasks"
author: Maxim Menshikov
layout: defect
permalink: /csharp/task
group:
   - csharp
---

Defects in how a `Task` is consumed, where asynchronous work is forced back into a synchronous wait. Blocking on a `Task` with `.Wait()`, `.Result`, or `GetAwaiter().GetResult()` ties up the calling thread and, on a captured synchronization context, can deadlock when the awaited continuation needs that same thread to finish.

The asynchronous chain is meant to be awaited all the way up; collapsing it to a blocking call also rewraps any fault in an `AggregateException`, obscuring the original error. Await the task instead of waiting on it.

