# State diagrams

Shows the lifecycle of one entity — the states it can be in and the transitions between them. Use when the question is "what states does X have and what causes transitions".

If you find yourself drawing more than one entity's states in the same diagram, you're conflating two state machines — split them.

## Start and end

Every state diagram needs at least a start. Most also need an end:

```puml
[*] --> Draft
...
Cancelled --> [*]
Paid --> [*]
```

`[*]` is the pseudo-state for entry/exit. Without it, the reader can't tell where the lifecycle begins.

## Simple transitions

```puml
[*] --> Draft
Draft --> Submitted : submit()
Submitted --> Paid : payment received
Submitted --> Cancelled : cancel()
Paid --> [*]
Cancelled --> [*]
```

The label after `:` is the trigger / event / guard. Keep labels short — long labels suggest the transition is doing too much.

## Composite states

When states cluster, nest them:

```puml
state Processing {
    [*] --> Validating
    Validating --> Charging : valid
    Validating --> Failed : invalid
    Charging --> Authorized : success
    Charging --> Failed : declined
    Authorized --> [*]
}

[*] --> Processing
Processing --> Paid : Authorized
Processing --> Refunded : Failed
```

Composite states give the diagram structure — flat lists of 15 states are unreadable.

## Concurrent regions

For parallel substates (rare in business domains, common in protocol/UI state):

```puml
state Session {
    state "Auth" as A {
        [*] --> Anonymous
        Anonymous --> LoggedIn : login
    }
    --
    state "Connection" as C {
        [*] --> Online
        Online --> Offline : disconnect
        Offline --> Online : reconnect
    }
}
```

The `--` (or `||`) separates concurrent regions inside one composite state. Use only when the two regions are genuinely independent.

## Pseudostates

PlantUML supports the standard UML pseudostates via stereotypes:

```puml
state choice1 <<choice>>
state fork1 <<fork>>
state join1 <<join>>
state h <<history>>
state H <<history*>>
```

### Choice (conditional branching)

```puml
state c1 <<choice>>
Validating --> c1
c1 --> Charging : [amount > 0]
c1 --> Failed : [amount <= 0]
```

Use `<<choice>>` instead of two un-conditioned transitions from one state — it makes the branching explicit.

### Fork / join (parallel)

```puml
state f <<fork>>
state j <<join>>
[*] --> f
f --> Validating
f --> Notifying
Validating --> j
Notifying --> j
j --> Done
```

### History

Resume a composite state at the most recent inner state:

```puml
state Paused {
    state h <<history>>
    state Step1
    state Step2
    state Step3
}
Active --> Paused : pause
Paused --> Active : resume → h
```

## Notes on states

```puml
note right of Submitted: cannot be edited
note left of Paid: triggers fulfillment
```

## Layout

Default is top-to-bottom. For wide lifecycles:

```puml
left to right direction
```

For state machines with many short labels, `skinparam linetype ortho` makes transitions easier to follow.

## Anti-patterns specific to state

- **No `[*]`.** Every state machine has an entry. Most have at least one terminal state. Show both.
- **Flat state list.** If states cluster, use composite states. A flat list of 12 states is almost always 3 composite states unwrapped.
- **Branching without `<<choice>>`.** Two transitions out of one state with different guards is a `<<choice>>` pseudostate.
- **Multiple entities in one diagram.** Each diagram tracks one entity. If you have a state for "Order" and a state for "Payment" both transitioning in the same diagram, split into two diagrams.
- **Transitions without triggers.** Every transition should have a label (event / guard / action). Unlabeled transitions imply they happen "automatically" — which is rarely what's meant.

## Template

See `templates/state.puml`.
