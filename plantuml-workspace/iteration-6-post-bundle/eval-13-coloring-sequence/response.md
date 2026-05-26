```puml
@startuml login-flow
!theme plain

' Participants — WebApp highlighted as the entry point via inline background color.
' AuthService keeps default styling per spec.
actor User
participant "WebApp" as Web #AED6F1
control "AuthService" as Auth

' Successful login: credentials in, token out.
User -> Web: POST /login {email, pwd}
Web -> Auth: verifyCredentials(email, pwd)
Auth --> Web: {ok, token}
Web --> User: 200 {token}

@enduml
```

Render: `plantuml -tsvg login-flow.puml`

Successful login flow: User posts credentials to WebApp (highlighted light blue as the entry point), which calls AuthService to verify and returns a token.
