Here's a PlantUML sequence diagram for the OAuth2 Authorization Code flow with PKCE.

```plantuml
@startuml
title OAuth2 Authorization Code Flow with PKCE

autonumber

actor "Browser" as Browser
participant "AuthServer" as Auth
participant "ResourceServer" as RS

== PKCE Setup ==
Browser -> Browser : generate code_verifier (random)
Browser -> Browser : code_challenge = BASE64URL(SHA256(code_verifier))

== Authorization Request ==
Browser -> Auth : GET /authorize\n(client_id, redirect_uri, code_challenge,\ncode_challenge_method=S256, state)
Auth -> Auth : authenticate user & obtain consent
Auth --> Browser : 302 redirect_uri?code=AUTH_CODE&state=...

== Token Exchange ==
Browser -> Auth : POST /token\n(grant_type=authorization_code,\ncode=AUTH_CODE, code_verifier, client_id, redirect_uri)
Auth -> Auth : verify SHA256(code_verifier) == stored code_challenge
Auth --> Browser : 200 { access_token, [refresh_token], expires_in }

== Resource Access ==
Browser -> RS : GET /resource\nAuthorization: Bearer ACCESS_TOKEN
RS -> RS : validate token (signature / introspection)
RS --> Browser : 200 protected resource

@enduml
```

Notes:
- `autonumber` numbers every message in order, as requested.
- `code_challenge_method=S256` is the recommended method (RFC 7636); `plain` exists but should be avoided.
- The `state` parameter mitigates CSRF; pair it with `nonce` if you're also using OIDC.
- PKCE removes the need for a client secret, which is why it's the recommended flow for SPAs and native/mobile apps (public clients).
- Render with any PlantUML renderer (e.g. `plantuml diagram.puml`, the VS Code PlantUML extension, or the online server at plantuml.com).
