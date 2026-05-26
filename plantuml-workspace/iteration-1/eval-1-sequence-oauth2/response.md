```puml
@startuml oauth2-pkce-login
!theme plain

participant Browser
participant AuthServer as Auth
participant ResourceServer as RS

autonumber

== PKCE setup ==
Browser -> Browser: generate code_verifier
Browser -> Browser: code_challenge = S256(code_verifier)

== Authorization request ==
Browser -> Auth: GET /authorize?client_id&redirect_uri&code_challenge&method=S256
Auth --> Browser: 302 redirect_uri?code=AUTH_CODE

== Token exchange ==
Browser -> Auth: POST /token {code=AUTH_CODE, code_verifier}
note right of Auth: verify S256(code_verifier) == stored code_challenge
Auth --> Browser: 200 {access_token}

== Resource access ==
Browser -> RS: GET /resource\nAuthorization: Bearer <access_token>
RS --> Browser: 200 {resource}

@enduml
```

Render: `plantuml -tsvg oauth2-pkce-login.puml`

OAuth2 Authorization Code + PKCE login: Browser generates `code_verifier` and derives `code_challenge`, hits `/authorize` to get an auth code, swaps code + verifier at `/token` for an access token, then calls ResourceServer with `Authorization: Bearer`.
