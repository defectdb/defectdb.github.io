---
title: "Disposal"
author: Maxim Menshikov
layout: defect
permalink: /csharp/dispose
group:
   - csharp
---

Defects in the lifetime of objects that hold unmanaged or scarce resources, where an `IDisposable` is allocated but never deterministically released. The garbage collector reclaims managed memory, but not file handles, sockets, database connections, or native buffers — those leak until a finalizer eventually runs, if one exists at all.

The fix is almost always a `using` statement or declaration that bounds the resource's life to its scope; the defect is the path where that scope is missing and `Dispose` is left to chance.

