# Sprites — technology-identity icons

Catalogue of sprite collections this skill knows how to include, the canonical include syntax for each, and the discipline around when to use them.

Sprites are **opt-in everywhere**. Default plantuml output stays dependency-free monochrome shapes — `database "Postgres"`, `queue "Kafka"`. Sprites layer on top when vendor / technology identity matters (data pipelines, system-design diagrams, mixed-vendor architectures). Even with sprites, **labels still carry the meaning** — a reader who renders monochrome or who is color-blind reads the same diagram.

## When sprites are worth adding

| Want | Add sprites |
|---|---|
| "Show our streaming pipeline so engineers recognize Kafka instantly" | Yes |
| Internal-only component diagram of one service | No (textual labels suffice) |
| Architecture diagram for an exec / non-technical reader | Yes (vendor logos read faster than text) |
| State machine / sequence / ER | No (sprites don't fit those types) |
| Anything PlantUML can already express clearly with `database`/`queue`/`cloud` keywords AND the audience knows the stack | No |

If in doubt, **skip them**. A monochrome diagram with good labels is always a fallback that works; a sprite-heavy diagram that didn't actually need them adds external `!include` URLs at render time for no information gain.

## The four collections this skill uses

### 1. `gilbarbara-plantuml-sprites` (default for data / infra technologies)

The single broadest plantuml-stdlib collection for data-infra logos. Covers Apache projects, databases, message brokers, observability tools, DevOps tooling.

**Include form** (URL only — *no* stdlib short-form `<gilbarbara/...>` despite what some older docs suggest):

```puml
!define SPRITESURL https://raw.githubusercontent.com/plantuml-stdlib/gilbarbara-plantuml-sprites/v1.1/sprites
!include SPRITESURL/kafka.puml
!include SPRITESURL/postgresql.puml
!include SPRITESURL/apache.puml
```

**Usage**: reference a sprite inside any shape with `<$<sprite-name>>`:

```puml
queue "<$kafka>\norders-topic" as orders_topic
database "<$postgresql>\norders-db" as orders_db
```

The `\n` puts the label on a second line so the icon and the label stack vertically.

**Confirmed sprites** (from the v1.1 release sprites-list — see https://github.com/plantuml-stdlib/gilbarbara-plantuml-sprites/blob/v1.1/sprites-list.md for the canonical list):

- **Streaming / messaging**: `kafka`, `pulsar`, `rabbitmq`, `activemq`
- **Big data / processing**: `spark`, `hadoop`, `airflow`, `apache` (generic), `databricks`
- **Databases**: `postgresql`, `mysql`, `mongodb`, `cassandra`, `redis`, `elasticsearch`, `clickhouse`, `mariadb`, `couchdb`, `dynamodb`, `sqlite`
- **Containers / orchestration**: `docker`, `kubernetes`, `nomad`, `consul`
- **Observability**: `prometheus`, `grafana`, `datadog`, `splunk`, `sentry`
- **DevOps / infra**: `terraform`, `ansible`, `jenkins`, `nginx`, `traefik`, `vault`
- **Cloud (vendor-logo form)**: `amazon-aws`, `microsoft-azure`, `google-cloud`

**Confirmed gap**: there is **no Apache Flink sprite** in this collection. See "The Flink gap" below.

### 2. `tupadr3/plantuml-icon-font-sprites` (devicons / font-awesome fallback)

When gilbarbara lacks a sprite, tupadr3 is the second choice. Uses a different reference pattern — prefix-macros, not `<$>`:

```puml
!define ICONURL https://raw.githubusercontent.com/tupadr3/plantuml-icon-font-sprites/v3.0.0/icons
!include ICONURL/common.puml
!include ICONURL/devicons2/mysql.puml
!include ICONURL/font-awesome-5/server.puml

DEV2_MYSQL(db1, "MySQL", database) FA5_SERVER(web1, "Web", node)
```

The macros are `DEV_*` (devicons), `DEV2_*` (devicons2 — refresh of devicons), `FA_*`/`FA5_*` (font-awesome / 5), `MAT_*` (material), `DEV4_*` etc. Naming depends on the icon set.

**When to reach for tupadr3**: if gilbarbara doesn't have the icon and tupadr3 does. Don't mix both libraries in one diagram unless you have to — the two reference syntaxes (`<$kafka>` vs `DEV2_MYSQL(...)`) look inconsistent side-by-side.

### 3. `awslib` / `aws-icons-for-plantuml` (AWS services)

Two versions exist:

- **Older, bundled in plantuml-stdlib**: `!include <aws/Storage/AmazonS3/AmazonS3>` — short-form, no version pin, ages out.
- **Current upstream, recommended**: pinned URL form (matches what `docs/example-renders/photo-sharing-arch.puml` uses):

```puml
!define AWSPuml https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/v23.0/dist
!include AWSPuml/AWSCommon.puml
!include AWSPuml/Storage/SimpleStorageService.puml

SimpleStorageService(bucket, "Photos bucket", "")
```

Macros are CamelCase service names: `SimpleStorageService` (S3), `SimpleQueueService` (SQS), `Lambda`, `RDS`, `DynamoDB`, `CloudFront`, `APIGateway`, `Cognito`, `EC2`, etc. Default to the **pinned upstream** form — current at the time of writing is `v23.0`.

### 4. `kubernetes-PlantUML` (Kubernetes resources)

Same pattern as AWS upstream — pinned URL:

```puml
!define KubernetesPuml https://raw.githubusercontent.com/dcasati/kubernetes-PlantUML/master/dist
!include KubernetesPuml/kubernetes_Common.puml
!include KubernetesPuml/OSS/KubernetesPod.puml
!include KubernetesPuml/OSS/KubernetesSvc.puml

KubernetesPod(api, "api-pod", "")
```

Macros are `Kubernetes*`: `KubernetesPod`, `KubernetesSvc`, `KubernetesIng`, `KubernetesDeploy`, `KubernetesSts`, `KubernetesPv`, `KubernetesNs`, `KubernetesCm`, `KubernetesSecret`, `KubernetesNode`.

(`master` is the only release channel published — for fully reproducible renders, pin to a specific commit SHA in place of `master`.)

## Mixing collections in one diagram

You can `!define` multiple include roots in one `.puml` and use them together:

```puml
' gilbarbara for streaming tech
!define SPRITESURL https://raw.githubusercontent.com/plantuml-stdlib/gilbarbara-plantuml-sprites/v1.1/sprites
!include SPRITESURL/kafka.puml
!include SPRITESURL/postgresql.puml

' AWS for managed services
!define AWSPuml https://raw.githubusercontent.com/awslabs/aws-icons-for-plantuml/v23.0/dist
!include AWSPuml/AWSCommon.puml
!include AWSPuml/Storage/SimpleStorageService.puml

' k8s for cluster-internal resources
!define KubernetesPuml https://raw.githubusercontent.com/dcasati/kubernetes-PlantUML/master/dist
!include KubernetesPuml/kubernetes_Common.puml
!include KubernetesPuml/OSS/KubernetesPod.puml

queue "<$kafka>\norders-topic" as orders
KubernetesPod(consumer, "consumer-pod", "")
SimpleStorageService(bucket, "events-bucket", "")
```

This is what `docs/example-renders/photo-sharing-arch.puml` does for AWS + k8s. The libraries are independent — no macro-name collisions across them.

**Cap**: don't pull in more than 2–3 sprite collections per diagram. Each one adds external fetch latency at render time. If you find yourself needing four, the diagram is probably trying to do too much — split it.

## The Flink gap

Apache Flink is **not in any of the four collections**. Concrete workaround the skill uses everywhere a Flink box appears:

```puml
!include SPRITESURL/apache.puml

node "<$apache>\nFlink job\n(streaming)" as flink
```

The generic Apache feather + the text label "Flink" works — readers recognize "Apache + streaming" instantly. Don't try to fake a Flink logo with random shapes; use the apache feather honestly and let the label do the work.

If Flink eventually lands in gilbarbara, swap `<$apache>` for `<$flink>` and drop the qualifier text. Track upstream: https://github.com/plantuml-stdlib/gilbarbara-plantuml-sprites/blob/main/sprites-list.md.

## C4-PlantUML integration

C4 has a first-class way to attach a sprite to a `Container` / `ContainerDb` / `ContainerQueue` via the `$sprite` argument — **prefer this over raw `<$kafka>` syntax inside a C4 diagram**, because raw sprite refs sidestep C4-PlantUML's styling and produce visually inconsistent diagrams.

```puml
!include <C4/C4_Container>

' Load the sprite resource so C4 can attach it.
!define SPRITESURL https://raw.githubusercontent.com/plantuml-stdlib/gilbarbara-plantuml-sprites/v1.1/sprites
!include SPRITESURL/kafka.puml

ContainerQueue(orders, "Orders Topic", "Kafka", "Event stream", $sprite="kafka")
```

The `$sprite="kafka"` argument tells C4-PlantUML to render the Kafka icon inside the standard C4 ContainerQueue shape. Same applies to `Container(..., $sprite="postgresql")`, etc.

## Anti-patterns

- **Sprite-only labels.** `queue "<$kafka>"` with no text. The icon alone fails monochrome and color-blind rendering. Always pair `<$kafka>` with a label.
- **Color-only emphasis on sprites.** If a Kafka sprite is "deprecated", say so in the label (`<$kafka>\nlegacy / deprecated`), not by tinting the icon red.
- **Mismatched icon and label.** `database "<$mysql>\nPostgres"` — picks the wrong sprite for the actual technology. The lint check `W092` catches some of these by name-matching `<$name>` against included sprite files.
- **Pulling 5+ sprite libraries.** Each `!define`/`!include` adds remote fetch on render. Cap at 2–3.
- **Unpinned URLs in committed `.puml`.** `master` works but breaks reproducibility. Pin to a release tag (`v1.1` for gilbarbara, `v23.0` for aws-icons, a specific commit SHA for k8s) whenever the diagram will be re-rendered later.

## Quick reference

| Need | Library | Include preamble | Reference syntax |
|---|---|---|---|
| Kafka / Postgres / Spark / Redis / etc. | gilbarbara | `!define SPRITESURL .../v1.1/sprites` + `!include SPRITESURL/<name>.puml` | `<$<name>>` |
| Icon gilbarbara lacks | tupadr3 | `!define ICONURL .../v3.0.0/icons` + `!include ICONURL/<set>/<name>.puml` | `<SET>_<NAME>(alias, label, type)` |
| AWS services | aws-icons-for-plantuml | `!define AWSPuml .../v23.0/dist` + `!include AWSPuml/AWSCommon.puml` + service includes | `SimpleStorageService(alias, label, "")` |
| k8s resources | kubernetes-PlantUML | `!define KubernetesPuml .../master/dist` + `!include KubernetesPuml/kubernetes_Common.puml` + resource includes | `KubernetesPod(alias, label, "")` |
| Flink | (none) | use `<$apache>` from gilbarbara | label says "Flink" |
