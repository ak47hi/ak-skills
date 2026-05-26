Pipeline diagram (left-to-right) for the streaming platform: Web + Mobile producers → Kafka topic → Flink job → fan-out to ClickHouse (analytics) and S3 (archival).

```puml
@startuml streaming-platform-pipeline
!theme plain

!define SPRITESURL https://raw.githubusercontent.com/plantuml-stdlib/gilbarbara-plantuml-sprites/v1.1/sprites
!include SPRITESURL/kafka.puml
!include SPRITESURL/apache.puml
!include SPRITESURL/amazon-aws.puml

left to right direction

' ---- Producers (left edge) ----
node "Web Clients" as web
node "Mobile Clients" as mobile

' ---- Transport / broker ----
queue "<$kafka>\nevents-topic" as events_topic

' ---- Stream processor ----
' Flink has no dedicated gilbarbara sprite — use <$apache> + "Flink" in label.
node "<$apache>\nFlink job\n(parse + enrich + route)" as flink

' ---- Sinks (right edge) ----
database "ClickHouse\n(analytics)" as clickhouse
cloud "<$amazon-aws>\nS3\n(archival, raw)" as s3

' ---- Flow ----
web    --> events_topic : "JSON events\n(HTTPS → Kafka producer)"
mobile --> events_topic : "JSON events\n(HTTPS → Kafka producer)"

events_topic --> flink : "Kafka consumer"

flink --> clickhouse : "batched inserts\n(JDBC / native protocol)"
flink --> s3         : "Parquet\n(hourly partitions)"

@enduml
```

Render: `plantuml -tsvg streaming-platform-pipeline.puml`
