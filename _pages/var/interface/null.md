---
title: "Null interface"
author: Maxim Menshikov
layout: defect
permalink: /var/interface/null
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: var.interface
group:
   - var
   - interface
---
The interface might be null causing panic

# Impact

Calling a method on a `nil` interface value, or dereferencing a `nil` value
carried inside an interface, triggers a runtime panic (`invalid memory address
or nil pointer dereference`). If the panic is not recovered it unwinds the
goroutine and, for the main goroutine, terminates the whole program. Even in a
server that recovers per request, the in-flight work is lost and the recovery
path adds load. The especially treacherous variant is the *typed nil*: an
interface holding a non-nil type but a nil concrete pointer compares `!= nil` yet
still panics when a method dereferences the receiver — so the usual `if x != nil`
guard passes and the program crashes anyway.

# Vulnerability potential

This issue has a real potential to contribute to denial of service.

1. A reachable nil-interface call is a crash-on-demand primitive: if an attacker
   can drive a request down a path where a dependency, decoded field, or returned
   error interface is nil, they can panic the goroutine repeatedly and degrade or
   take down the service.
2. The typed-nil pitfall defeats naive nil checks, so error-handling code that
   "looks" safe can still be crashed, widening the set of reachable panic sites.

Memory-safety/code-execution risk is negligible: Go's runtime turns the bad
access into a controlled panic rather than corruption, so the threat is
availability.

# Technical details

An interface value is a pair `(type, value)`. It is `nil` only when *both* halves
are nil. A method call on a nil interface has no type to dispatch on and panics
immediately.

## The typed-nil trap
Assigning a nil concrete pointer to an interface yields an interface whose type
half is set and value half is nil — so the interface is **not** equal to `nil`:

```go
var p *T = nil
var i I = p   // i != nil, but i holds a nil *T
```

A subsequent `i.Method()` dispatches fine but panics if the method dereferences
its nil receiver. This commonly bites when a function returns a concrete
`*MyError` as an `error` interface: returning a nil `*MyError` produces a non-nil
`error`, so callers' `if err != nil` wrongly fires (or, when they then use it,
panics).

## Where nils come from
Unset struct fields of interface type, map lookups that miss, optional
dependencies never wired up, and functions that return `nil, nil`.

# Catching the issue

## Static analysis
`go vet` and `golangci-lint` (`nilness`, `nilerr`, `staticcheck` SA4023 for the
typed-nil-error comparison) flag many nil and typed-nil mistakes. Enable
`staticcheck` in CI.

## Defensive coding and recovery
Guard interface calls with explicit nil checks, but be aware they do not catch
typed nils — return the interface type directly (`return nil`) rather than a
typed nil pointer. For servers, install a `recover()` in a deferred function at
the goroutine/request boundary so one nil call cannot take the process down, and
log the panic for triage.

## Tests
Run with the race detector and exercise the nil/empty-dependency paths;
table-driven tests that pass nil arguments surface these quickly.

# How to reproduce

Run the program; it prints that `err != nil` and then panics, despite the
function appearing to return "no error" — the typed-nil interface.

```go
package main

import "fmt"

type MyError struct{ msg string }

func (e *MyError) Error() string { return e.msg } // dereferences e

func doWork(fail bool) error {
	var e *MyError // nil concrete pointer
	if fail {
		e = &MyError{"boom"}
	}
	return e // BUG: returns a non-nil error interface holding a nil *MyError
}

func main() {
	err := doWork(false)
	fmt.Println("err != nil:", err != nil) // true, even though "no error"
	fmt.Println(err.Error())               // panics: nil pointer dereference
}
```
