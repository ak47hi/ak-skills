```puml
@startuml oauth2-pkce-login
!theme plain

participant Browser
participant AuthServer
participant ResourceServer

autonumber

Browser -> Browser: generate code_verifier
Browser -> Browser: code_challenge = SHA256(code_verifier)
Browser -> AuthServer: GET /authorize?code_challenge&method=S256
AuthServer --> Browser: 302 redirect with authorization code
Browser -> AuthServer: POST /token (code + code_verifier)
AuthServer --> Browser: access_token
Browser -> ResourceServer: GET /resource (Authorization: Bearer access_token)
ResourceServer --> Browser: 200 protected resource

@enduml
```

```bash
plantuml -tsvg oauth2-pkce-login.puml
```

Sequence diagram of the OAuth2 PKCE login flow: Browser generates verifier/challenge, exchanges challenge for auth code at AuthServer, swaps code+verifier for an access token, then calls ResourceServer with the token; autonumbered.
