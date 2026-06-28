---
title: "Sleep in interrupt"
author: Maxim Menshikov
layout: defect
permalink: /context/interrupt/sleep
arch:
   - native
vulnerability:
   - Low
ddos:
   - Medium
group_full: context.interrupt
group:
   - context
   - interrupt
---
Sleep in interrupt is usually not possible

# Impact

Calling a blocking/sleeping primitive from interrupt (atomic) context is illegal
on virtually every operating system and bare-metal runtime. An interrupt handler
runs to completion with no associated schedulable task, so there is nothing for
the scheduler to put to sleep and nothing to wake. Depending on the platform the
result ranges from a hard kernel panic, to a silently wedged interrupt line, to
data corruption when the scheduler is re-entered from a context it must never run
in.

Because the handler often runs with further interrupts masked, a sleep there can
stall timekeeping, starve other devices, and hang the entire core rather than just
the current task.

# Vulnerability potential

The realistic threat is denial of service.

1. If the interrupt that reaches the sleeping path can be triggered by external
   input (a crafted packet, a device the attacker controls, a timer they can
   provoke), they can deadlock or panic the kernel on demand — a remote or local
   DoS.
2. A handler that sleeps while holding a spinlock can deadlock every other CPU
   spinning on that lock, taking the whole machine down.

It is not, by itself, a memory-corruption or code-execution primitive, so the
security rating is `Low`; the crash/hang potential gives it a `Medium` DoS rating.

# Technical details

Interrupt context (also called atomic or "top half" context) has no backing
`task_struct`/TCB and frequently runs with preemption and/or interrupts disabled.
The scheduler's invariant is that it is only ever entered from a sleepable
(process/thread) context.

## Linux kernel
Sleeping functions — `msleep`, `schedule`, `mutex_lock`, `kmalloc(GFP_KERNEL)`,
`copy_from_user`, anything that "might sleep" — must not be called from hard IRQ
handlers, softirqs, tasklets, or while holding a spinlock. Doing so trips
`might_sleep()` and yields "BUG: scheduling while atomic" / "sleeping function
called from invalid context". Defer the work to a workqueue or threaded IRQ
instead.

## RTOS / bare metal (FreeRTOS, Zephyr, etc.)
Inside an ISR you must use the FromISR API variants (`xQueueSendFromISR`) and may
never call `vTaskDelay`, blocking semaphore takes, or `vTaskSuspend`. Blocking in
an ISR corrupts the RTOS state or faults, because the kernel scheduler is not
designed to be invoked from that vector.

## Busy-wait nuance
A bounded busy-wait (e.g. `udelay`) is permitted because it does not yield the
CPU; it is the *sleeping/blocking* (scheduler-yielding) call that is illegal. The
two are easy to confuse.

# Catching the issue

## Kernel build options
Enable `CONFIG_DEBUG_ATOMIC_SLEEP` (and lockdep) so the kernel actively reports
sleeping-in-atomic at runtime with a backtrace pinpointing the call site.

## Static analysis
Sparse annotations and analyzers (including the one emitting this diagnostic) flag
calls to known-sleeping functions on paths that originate in an interrupt handler.
Coccinelle scripts can match ISR bodies that call blocking APIs.

## Design discipline
Keep ISRs minimal: acknowledge the device, capture data, signal a bottom half
(workqueue, threaded IRQ, task notification) and return. Centralize all blocking
work in process context. Code-review rule: no allocation with `GFP_KERNEL`, no
mutex, no delay in any function reachable from an interrupt vector.

# How to reproduce

This minimal Linux kernel module sleeps inside a timer (softirq) callback. Load it
and watch the kernel log: with atomic-sleep debugging enabled it reports a
"scheduling while atomic" / "sleeping function called from invalid context" BUG.

```c
#include <linux/module.h>
#include <linux/timer.h>
#include <linux/delay.h>

static struct timer_list t;

static void on_tick(struct timer_list *unused)
{
    /* Timer callbacks run in softirq (atomic) context. msleep() may
       sleep, which is illegal here and trips the scheduler invariant. */
    msleep(100);
}

static int __init demo_init(void)
{
    timer_setup(&t, on_tick, 0);
    mod_timer(&t, jiffies + HZ);
    return 0;
}

static void __exit demo_exit(void) { del_timer_sync(&t); }

module_init(demo_init);
module_exit(demo_exit);
MODULE_LICENSE("GPL");
```
