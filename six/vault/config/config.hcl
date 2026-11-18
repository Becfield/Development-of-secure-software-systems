ui = true
disable_mlock = true

storage "file" {
  path = "/vault/file"
}

# Listener задаётся в docker-compose через VAULT_DEV_LISTEN_ADDRESS (dev-режим).
# Здесь его дублировать нельзя - иначе "bind: address already in use".
