```puml
@startuml login-sequence
!theme plain

actor User
participant "WebApp" as Web #AED6F1
control "AuthService" as Auth

User -> Web: POST /login {email, password}
Web -> Auth: verifyCredentials(email, password)
Auth --> Web: {ok, token}
Web --> User: 200 OK {token}

@enduml
```

```bash
plantuml -tsvg login-sequence.puml
```

Sequence diagram of a successful login: User posts credentials to WebApp (highlighted light blue as the entry point), which delegates to AuthService and returns a token.
