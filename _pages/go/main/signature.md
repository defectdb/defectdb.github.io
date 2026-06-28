---
title: "Invalid signature for main()"
author: Maxim Menshikov
layout: defect
permalink: /go/main/signature
arch:
   - native
vulnerability:
   - None
ddos:
   - None
group_full: go.main
group:
   - go
   - main
---
Go's `func main` in package main must take no parameters and return no value; the compiler rejects any other signature

# Impact

In Go, the program entry point must be declared exactly as `func main()` in
`package main`: no parameters and no results. Declaring it with arguments
(`func main(args []string)`), a return value (`func main() int`), or as a method
or generic function makes the build fail with "func main must have no arguments
and no return values". The consequence is purely a compile error — no binary is
produced, so there is no runtime impact. The defect usually reflects habits
carried from C (`int main(int argc, char **argv)`) or other languages; in Go,
command-line arguments and exit codes are obtained through different mechanisms.

# Vulnerability potential

This defect has no security relevance. The compiler rejects the program, so no
faulty executable exists to attack. It is a build-time correctness issue only.

# Technical details

The Go runtime calls `main.main` with no arguments and ignores any return value;
the language spec therefore fixes its signature. The toolchain enforces this in
the type checker before code generation.

## Getting arguments and exit codes the Go way

Command-line arguments are read from `os.Args` (a `[]string`, where `os.Args[0]`
is the program name), or parsed via the `flag` package. The process exit status
is set with `os.Exit(code)` (note: `os.Exit` skips deferred functions), or by
letting `main` return normally for exit code 0. There is no `argc/argv`
parameter and no integer return as in C.

## Related constraints

`package main` must also contain a `main` function for `go build` to produce an
executable; an `init` function may exist alongside it but cannot replace it.
`func main` cannot have type parameters.

# Catching the issue

## The compiler

`go build` / `go vet` reject a wrongly-typed `main` unconditionally; this can
never reach a running program, so no runtime tooling is required.

## Editor and review

`gopls` (the Go language server) flags the bad signature in-editor immediately.
In review, simply confirm the entry point is `func main()` with empty parameter
and result lists, and that arguments/exit codes go through `os.Args`/`flag` and
`os.Exit`.

# How to reproduce

Observe that this does not compile: "func main must have no arguments and no
return values".

```go
package main

func main() int { // invalid: main must take no params and return nothing
	return 0
}
```
