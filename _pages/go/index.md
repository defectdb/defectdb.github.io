---
title: "Go"
author: Maxim Menshikov
layout: defect
permalink: /go
---

Defects specific to the Go language and its runtime — cases where idiomatic-looking code violates a rule the toolchain enforces or the runtime assumes. Go trades a small, opinionated surface for strict conventions, and breaking one of those conventions tends to fail loudly at build or startup rather than degrade quietly.

This section collects the language's own footguns, beginning with the program entry point: the `main` function in `package main` whose exact shape the runtime expects before it will hand control to user code.
