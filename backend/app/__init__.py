import truststore

# Windows (and some corporate networks) trust root CAs via the OS certificate
# store, which curl/Schannel use but Python's bundled certifi list doesn't.
# This makes httpx/openai (and anything else using ssl.SSLContext) verify
# against the OS store instead, matching what curl already does successfully.
truststore.inject_into_ssl()
