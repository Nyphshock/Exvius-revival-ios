# Multi-User Auto-Registration

## Overview

Il sistema ora supporta l'**auto-registrazione automatica** per i nuovi dispositivi. Quando un nuovo IP di Tailscale si connette al server, viene automaticamente assegnato un ID profilo unico senza richiedere configurazione manuale.

## Flusso di Funzionamento

### Primo Accesso da un Nuovo Dispositivo

```
1. Nuovo dispositivo (IP Tailscale sconosciuto) si connette
         ↓
2. Server genera automaticamente un nuovo player_id univoco
         ↓
3. Server crea un file di profilo vuoto: /state/profiles/{player_id}.json
         ↓
4. Server salva il mapping nel profiles.json:
   "100.x.y.z": "100000002"  (nuovo IP → nuovo ID)
         ↓
5. Gioco carica il profilo vuoto
         ↓
6. Mostra schermata "Crea Nuovo Giocatore"
         ↓
7. Utente inserisce il nome
         ↓
8. Gioco invia CreateUserRequest con il nome
         ↓
9. Server aggiorna il profilo con il nome:
   identity.handle_name = "Nome Giocatore"
         ↓
10. Profilo completo salvato
         ↓
11. Giocatore entra nella HOME con profilo nuovo e vuoto
```

### Secondo Accesso dallo Stesso Dispositivo

```
1. Stesso dispositivo (IP già mappato) si connette
         ↓
2. Server legge profiles.json, trova il mapping:
   "100.x.y.z" → "100000002"
         ↓
3. Server carica il profilo esistente: /state/profiles/100000002.json
         ↓
4. Giocatore torna al suo save, allo stesso punto dove l'ha lasciato
```

## Cosa Cambia nel Sistema

### Prima (Configurazione Manuale)

```json
{
  "version": 1,
  "default_player_id": "100000001",
  "clients": {
    "100.64.123.45": "100000001"
  }
}
```

L'utente doveva:
1. Trovare l'IP del dispositivo nella console Tailscale
2. Editare manualmente `profiles.json`
3. Aggiungere il mapping
4. Riavviare il server

❌ Tedioso e soggetto a errori

### Dopo (Auto-Registrazione)

```json
{
  "version": 1,
  "default_player_id": "100000001",
  "clients": {
    "100.64.123.45": "100000001",
    "100.64.123.46": "100000002",      // Auto-aggiunto al primo accesso
    "100.65.200.10": "100000003"       // Auto-aggiunto al primo accesso
  }
}
```

✅ Automatico, istantaneo, zero configurazione

## Modifche nel Codice

### `player_profiles.py`

#### Nuovo Metodo: `_auto_register_client()`
```python
def _auto_register_client(self, address: str) -> str:
    """Auto-register a new device without requiring a name yet."""
    player_id = self._next_player_id()
    profile = self._load_profile(player_id)
    self._clients[address] = player_id
    self._save_client_map()
    self._profiles[player_id] = profile
    return player_id
```

**Cosa fa:**
- Genera un nuovo ID univoco
- Crea il file di profilo
- Salva il mapping nel `profiles.json`
- Ritorna l'ID al gioco

#### Metodo Modificato: `activate()`
```python
if player_id is None:
    if registration_name is None:
        # Auto-register unknown devices con nuovo ID
        player_id = self._auto_register_client(address)
    else:
        # Registrazione con nome da CreateUserRequest
        player_id = self._register_client(address, registration_name)
```

**Cosa cambia:**
- Prima: Lanciava `UnregisteredClientError` se l'IP non era mappato
- Dopo: Chiama `_auto_register_client()` per creare automaticamente il mapping

#### Metodo Modificato: `_register_client()`
```python
existing_player_id = self._clients.get(address)
if existing_player_id:
    # Aggiorna il profilo auto-registrato con il nome
    profile.player.data["identity"]["handle_name"] = handle_name.strip()
    return existing_player_id
```

**Cosa cambia:**
- Verifica se l'indirizzo è già mappato (auto-registrato)
- Se sì, aggiorna solo il nome del profilo esistente
- Se no, crea un nuovo mapping come prima

## Log del Server

### Auto-Registrazione
```
[ios-server] profiles: auto-registered 100.64.123.46 as player 100000002 (awaiting player name)
```

### Nome Impostato
```
[ios-server] profiles: 100.64.123.46 named their profile 'Mio Nome' (player 100000002)
```

## Profili Separati - Conferma

Ogni dispositivo ha:

✅ **File di Save Separato**
- Device A → `/state/profiles/100000001.json`
- Device B → `/state/profiles/100000002.json`
- Device C → `/state/profiles/100000003.json`

✅ **Identità Univoca**
- Device A → `identity.user_id = "100000001"`
- Device B → `identity.user_id = "100000002"`
- Device C → `identity.user_id = "100000003"`

✅ **Progress Totalmente Separato**
- Denaro/Lapis
- Personaggi/Unit
- Quest completate
- Livello
- Battle data
- Equipaggiamento
- Ecc.

**Nessun dato viene condiviso tra profili** se non sono esplicitamente mappati allo stesso ID.

## Gestione Manuale (Opzionale)

Se necessario, l'utente può ancora:

1. Condividere lo stesso profilo tra più dispositivi:
```json
{
  "version": 1,
  "default_player_id": "100000001",
  "clients": {
    "100.64.123.45": "100000001",
    "100.64.123.46": "100000001"     // Stesso ID = stesso profilo
  }
}
```

2. Cambiare il mapping manualmente in `profiles.json`
3. Aggiungere/rimuovere dispositivi

Il server ricaricherà il file `profiles.json` automaticamente al prossimo accesso (polling ogni richiesta).

## Scenari di Utilizzo

### Scenario 1: Famiglia con più device
- Papà con iPhone → ID 100000001 → Profilo Papà
- Mamma con Android → ID 100000002 → Profilo Mamma
- Figlio con iPad → ID 100000003 → Profilo Figlio

Tutto automatico! Niente configurazione manuale.

### Scenario 2: Stesso utente più device
- PC Server locale con Tailscale
- iPhone
- Android

Stesso utente accede da 3 device:
1. Crea profilo da iPhone → auto-registrato come 100000002
2. Accede da Android → auto-registrato come 100000003
3. Modifica `profiles.json` per puntare entrambi allo stesso ID se vuole sincronizzare

```json
{
  "clients": {
    "100.64.123.45": "100000002",
    "100.65.200.10": "100000002"     // Stesso profilo
  }
}
```

Accesso successivo da Android carica lo stesso save che aveva su iPhone.

## Compatibilità

✅ **Completamente backward-compatible**
- Il file `profiles.json` manuale continua a funzionare
- I vecchi mapping rimangono intatti
- I nuovi dispositivi si auto-registrano
- Il sistema convive perfettamente con entrambi gli approcci
