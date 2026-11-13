# Multi-User Auto-Registration

## Overview

Il sistema ora supporta l'**auto-registrazione automatica** per i nuovi dispositivi. Quando un nuovo IP di Tailscale si connette al server, viene automaticamente assegnato un ID profilo unico senza richiedere configurazione manuale.

Il server iOS crea `profiles.json` se manca. I nuovi ID partono da `300000001`; i mapping esistenti non vengono modificati. Il salvataggio predefinito resta disponibile, ma per usarlo da un dispositivo occorre associare manualmente il suo IP a `default_player_id`. Fai un backup di `server/state/` prima di modificare i mapping.

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
   "100.x.y.z": "300000001"  (nuovo IP → nuovo ID)
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
   "100.x.y.z" → "300000001"
         ↓
3. Server carica il profilo esistente: /state/profiles/300000001.json
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
    "100.64.123.46": "300000001",
    "100.65.200.10": "300000002"
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

Se la prima richiesta del dispositivo è `CreateUserRequest`, `_register_client()` crea direttamente il profilo con il nome scelto. Per un dispositivo già registrato, la richiesta viene gestita usando il profilo associato.

## Log del Server

### Auto-Registrazione
```
[ios-server] profiles: auto-registered 100.64.123.46 as player 300000001 (awaiting player name)
```

### Registrazione con Nome
```
[ios-server] profiles: registered 100.64.123.46 as player 300000001 ('Mio Nome')
```

## Profili Separati - Conferma

Ogni dispositivo ha:

✅ **File di Save Separato**
- Salvataggio predefinito → slot preesistente
- Device B → `/state/profiles/300000001.json`
- Device C → `/state/profiles/300000002.json`

✅ **Identità Univoca**
- Device A → `identity.user_id = "100000001"`
- Device B → `identity.user_id = "300000001"`
- Device C → `identity.user_id = "300000002"`

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
Se rimuovi un mapping, al prossimo accesso quell'IP riceve un nuovo profilo: il vecchio salvataggio non viene cancellato e si può recuperare ripristinando il mapping. L'identificazione avviene tramite l'IP visto dal server, non tramite autenticazione: dispositivi dietro lo stesso proxy o indirizzo non sono distinguibili e le connessioni loopback usano il salvataggio predefinito.

## Scenari di Utilizzo

### Scenario 1: Famiglia con più device
- Papà con iPhone → ID 100000001 → Profilo Papà
- Mamma con Android → ID 300000001 → Profilo Mamma
- Figlio con iPad → ID 300000002 → Profilo Figlio

Tutto automatico! Niente configurazione manuale.

### Scenario 2: Stesso utente più device
- PC Server locale con Tailscale
- iPhone
- Android

Stesso utente accede da 3 device:
1. Crea profilo da iPhone → auto-registrato come 300000001
2. Accede da Android → auto-registrato come 300000002
3. Modifica `profiles.json` per puntare entrambi allo stesso ID se vuole sincronizzare

```json
{
  "clients": {
    "100.64.123.45": "300000001",
    "100.65.200.10": "300000001"
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
