```puml
@startuml oauth2-pkce-login
!theme plain

boundary Browser
participant AuthServer
participant ResourceServer

autonumber

note left of Browser: generate code_verifier\nderive code_challenge = S256(code_verifier)

Browser -> AuthServer: GET /authorize?client_id&code_challenge&method=S256
AuthServer --> Browser: 302 redirect with auth code

Browser -> AuthServer: POST /token { code, code_verifier }
note right of AuthServer: verify S256(code_verifier)\nmatches stored code_challenge
AuthServer --> Browser: { access_token }

Browser -> ResourceServer: GET /resource\nAuthorization: Bearer <access_token>
ResourceServer --> Browser: 200 { resource }

@enduml
```

Render: `plantuml -tsvg diagram.puml`

OAuth2 Authorization Code with PKCE login flow: Browser derives `code_challenge` from a locally-generated `code_verifier`, gets an auth code from `AuthServer`, exchanges code plus verifier for an `access_token`, then calls `ResourceServer` as a bearer.
