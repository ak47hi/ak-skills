```puml
@startuml login-flow-sequence
!theme plain

actor User
participant "WebApp" as Web #AED6F1
participant "AuthService" as Auth

User -> Web: submit credentials (email, password)
Web -> Auth: POST /authenticate {email, password}
Auth --> Web: 200 {token, userId}
Web --> User: 200 OK (session established)

@enduml
```

Render: `plantuml -tsvg login-flow-sequence.puml`

Successful login flow: User submits credentials to WebApp (highlighted #AED6F1 as the entry point), which calls AuthService and returns a session token back to the user.
