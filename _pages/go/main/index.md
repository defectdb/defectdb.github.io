---
title: "Entry point"
author: Maxim Menshikov
layout: defect
permalink: /go/main
group:
   - go
---

Defects in the program's entry point, where the declared `main` does not match the signature the Go runtime requires. The entry function in `package main` must be `func main()` — no parameters, no return values — and any deviation, such as adding arguments or a return type, is rejected by the compiler or leaves the package without a usable entry point rather than starting the program.
