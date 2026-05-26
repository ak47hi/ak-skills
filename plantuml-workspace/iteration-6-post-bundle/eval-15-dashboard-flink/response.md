Flink job graph (dashboard-mimicry mode) — KafkaSource (p=4) → keyBy/Map (p=4) → Sink (p=1), rendered with Flink-blue operator boxes and HASH/FORWARD edge labels matching the Flink Web UI.

```puml
@startuml flink-jobgraph-kafka-map-sink
left to right direction
skinparam backgroundColor white
skinparam defaultFontSize 10
skinparam rectangle {
  BackgroundColor #4A90D9
  FontColor white
  BorderColor #2C5F8A
  RoundCorner 8
  Shadowing false
}
skinparam arrow {
  Color #666666
  FontSize 9
}

' Operators — base Flink-blue for unchanged operators
rectangle "Source:\nKafkaSource\n---\n**Parallelism: 4**" as SRC
rectangle "keyBy/Map\n---\n**Parallelism: 4**" as MAP
rectangle "Sink\n---\n**Parallelism: 1**" as SNK

' Edges — Flink shuffle vocabulary
SRC --> MAP : HASH (key)
MAP --> SNK : FORWARD

legend bottom
  |= Edge Label |= Meaning |
  | HASH | keyBy shuffle (partitioned by key) |
  | FORWARD | No shuffle (chained, 1:1 between subtasks) |
  | REBALANCE | Round-robin shuffle |
  |<#4A90D9> Dark blue box | Unchanged operator |
endlegend

@enduml
```

Render:

```
plantuml -tsvg diagram.puml
```
