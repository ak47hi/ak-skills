```puml
@startuml login-flow-sequence
!theme plain

actor User
participant WebApp #AED6F1
participant AuthService

User -> WebApp: POST /login {email, password}
WebApp -> AuthService: verifyCredentials(email, password)
AuthService --> WebApp: {ok, token}
WebApp --> User: 200 OK {token}

@enduml
```

```bash
plantuml -tsvg login-flow-sequence.puml
```

Sequence diagram of a successful login: User -> WebApp -> AuthService and back, with WebApp shaded light blue (#AED6F1) to mark it as the entry point.
