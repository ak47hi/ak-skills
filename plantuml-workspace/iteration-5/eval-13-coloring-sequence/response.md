```puml
@startuml login-sequence
!theme plain

actor User
participant "WebApp" as WebApp #AED6F1
control "AuthService" as Auth

User -> WebApp: POST /login {email, password}
WebApp -> Auth: verifyCredentials(email, password)
Auth --> WebApp: {ok, token}
WebApp --> User: 200 OK {token}

@enduml
```

```bash
plantuml -tsvg login-sequence.puml
```

Sequence diagram of a successful login flow: User submits credentials to WebApp (highlighted light-blue as the entry point), WebApp verifies them with AuthService, and a token is returned to the User.
