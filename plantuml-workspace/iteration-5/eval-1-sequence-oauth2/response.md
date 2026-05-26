```puml
@startuml oauth2-pkce-login
!theme plain

participant Browser
control AuthServer
participant ResourceServer

autonumber

Browser -> Browser: generate code_verifier
Browser -> Browser: code_challenge = SHA256(code_verifier)
Browser -> AuthServer: GET /authorize?client_id&code_challenge&method=S256
AuthServer --> Browser: 302 redirect with auth code
Browser -> AuthServer: POST /token {code, code_verifier}
AuthServer -> AuthServer: verify SHA256(code_verifier) == code_challenge
AuthServer --> Browser: 200 {access_token}
Browser -> ResourceServer: GET /resource (Authorization: Bearer access_token)
ResourceServer --> Browser: 200 {resource}

@enduml
```

```bash
plantuml -tsvg oauth2-pkce-login.puml
```

Sequence diagram of the OAuth2 PKCE login flow: Browser generates verifier/challenge, requests /authorize, exchanges code + verifier at /token, then calls ResourceServer with the access token, with autonumbering.
