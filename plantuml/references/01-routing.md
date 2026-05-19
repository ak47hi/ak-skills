# Routing

Pick exactly one diagram type per `.puml` file. If a request honestly needs two diagrams, produce two files — don't mix levels in one.

## Before routing: is PlantUML even the right tool?

Check `references/92-not-plantuml.md` first. If the request is an **exit case** (Mermaid for GitHub-native rendering; gantt / journey / mindmap / gitGraph / sankey / quadrant; D2 for "make it look good"; Excalidraw-style whiteboarding), **name the better tool and stop** — don't produce PlantUML the user will throw away.

The user can always override ("produce PlantUML anyway"), in which case drop back into the decision tree below.

## Intent → type decision tree

Walk top to bottom. First match wins.

```
Is the user asking about behavior over time (messages, calls, ordering)?
  └─ Yes → are participants software components/services, not procedure steps?
        └─ Yes → SEQUENCE          (10-sequence.md / sequence.puml)
        └─ No  → ACTIVITY           (14-activity.md / activity.puml)

Is the user describing a lifecycle / states of one entity?
  └─ Yes → STATE                    (13-state.md / state.puml)

Is the user describing object-oriented type structure (classes, inheritance, generics)?
  └─ Yes → CLASS                    (12-class.md / class.puml)

Is the user describing a data model (entities + cardinality)?
  └─ Yes → ER                       (16-er.md / er.puml)

Is the user describing actor goals against a system?
  └─ Yes → USE CASE                 (17-usecase.md / usecase.puml)

Is the user describing where things run (hosts, pods, infra)?
  └─ Yes → DEPLOYMENT               (15-deployment.md / deployment.puml)

Is the user describing static software structure (services + interfaces)?
  └─ Yes → is the user explicitly asking for C4 OR is the audience non-technical / business?
        └─ Yes → C4                  (18-c4.md / c4-*.puml)
        └─ No  → COMPONENT           (11-component.md / component.puml)
```

## C4 sub-routing

If C4 is the chosen family, pick exactly one level:

| Question the diagram answers | C4 level | Template |
|---|---|---|
| Who uses our system, and which external systems does it integrate with? | Context | `templates/c4-context.puml` |
| What are the high-level containers (apps, services, datastores) inside our system, and how do they talk? | Container | `templates/c4-container.puml` |
| What are the components inside ONE container, and how do they collaborate? | Component | `templates/c4-component.puml` |
| What's the runtime call flow for ONE scenario across our containers? | Dynamic | `templates/c4-dynamic.puml` |

**Hard rule:** don't mix levels in one diagram. Showing internal components inside a Context diagram, or external users inside a Component diagram, breaks C4. See `references/18-c4.md` § "Abstraction-level discipline".

## Common ambiguities and how to resolve

### Sequence vs activity

Both show flow. Heuristic:
- **Sequence** when the actors are distinct entities exchanging messages (services, classes, users).
- **Activity** when there's one notional executor and you're describing the *procedure* (steps, branches, loops, swimlanes).

If the user mentions "swimlanes" explicitly → activity.

### Sequence vs C4 dynamic

Both can show calls between services over time. Heuristic:
- **C4 dynamic** when the participants are C4-styled containers and the audience is broader (architecture review, onboarding).
- **Sequence** when the participants are finer-grained (classes, internal modules) or when the audience is engineers familiar with the system.

### Component vs deployment

Both show "boxes and lines". Heuristic:
- **Component** when the question is *what* the software is made of.
- **Deployment** when the question is *where* it runs (hosts, pods, regions, clouds).

If both matter, produce two diagrams.

### Component vs C4 container

Component is older UML; C4 Container is the C4 framework's equivalent at the same abstraction level. Heuristic:
- **C4 container** when the user said "C4", or the audience includes non-developers.
- **Component** when the user said "UML component diagram", or the diagram needs UML-specific features (ports, lollipop interfaces).

### Class vs ER

Both describe data. Heuristic:
- **Class** for OO domain models (with methods, inheritance, generics).
- **ER** for relational schemas (with PK/FK, cardinality, no methods).

If the user mentions "tables", "schema", "primary key", "foreign key" → ER.

## Multi-diagram requests

If the user asks for "an architecture diagram", produce **one** C4 container diagram. If they want more depth, generate additional diagrams in follow-up turns — don't unilaterally produce a multi-diagram dump.

If they explicitly ask for multiple (e.g. "context + container"), generate both as separate `.puml` files with distinct names.
