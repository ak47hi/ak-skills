```puml
@startuml login-sequence
!theme plain

actor User
participant "WebApp" as Web #AED6F1
control "AuthService" as Auth

User -> Web: POST /login {email, password}
Web -> Auth: verifyCredentials(email, password)
Auth --> Web: {ok, token}
Web --> User: 200 {token}

@enduml
```

```bash
plantuml -tsvg login-sequence.puml
```

Sequence diagram of a successful login: User to WebApp (highlighted light blue as the entry point) to AuthService and back, returning a token to the user.
