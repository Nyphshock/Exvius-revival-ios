# Android Certificate Support - Changes Summary

## Overview
Il server ora genera e serve il certificato CA sia per iOS che per Android.

## Modifiche Effettuate

### 1. `ios-server/serve.py`

#### Funzione `make_handler()` (linea ~125)
**Prima:** Accettava parametri per `profile` (iOS) e `ca_der` (certificato)
**Dopo:** Ora accetta anche `ca_pem` per il certificato in formato PEM per Android

**Nuovi endpoint:**
- `/ca.pem` - Scarica il certificato CA in formato PEM (per Android)
- `/__exvius/ca.pem` - Alternativa dello stesso endpoint

**Endpoint esistenti:**
- `/ca.mobileconfig` - Profilo iOS (non modificato)
- `/ca.crt` - Certificato CA in formato DER (non modificato)

#### Funzione `main()` (linea ~375)
**Prima:**
```python
handler = make_handler(capture_server, paths['profile'].read_bytes(), paths['ca_der'].read_bytes())
log(f'ready. Certificate profile for the phone: http://{where}/ca.mobileconfig')
```

**Dopo:**
```python
handler = make_handler(capture_server, paths['profile'].read_bytes(), paths['ca_der'].read_bytes(), 
                      paths['ca_pem'].read_bytes())
log(f'ready. Certificate profile for the phone: http://{where}/ca.mobileconfig')
log(f'Android certificate: http://{where}/ca.pem')
```

### 2. `ios-server/certs.py`

#### Funzione `ensure()` (linea ~130)
**Prima:** Restituiva il dizionario senza `ca_pem`
**Dopo:** Aggiunge `'ca_pem': folder / 'ca.pem'` al dizionario di ritorno

Il file `ca.pem` già esisteva (generato da `_make_root()`), ora è semplicemente esposto e servito dal server.

## Certificati Generati

Il sistema crea automaticamente:
- `/srv/ffbe/server-root/certs/ca.key` - Chiave privata CA
- `/srv/ffbe/server-root/certs/ca.pem` - Certificato CA in formato PEM (nuovo per Android)
- `/srv/ffbe/server-root/certs/ca.crt` - Certificato CA in formato DER (per iOS e download)
- `/srv/ffbe/server-root/certs/exvius-offline.mobileconfig` - Profilo iOS

## Come Usare

### Per iOS
L'utente apre il browser e va a:
```
http://<server-ip>/ca.mobileconfig
```
Oppure tramite Tailscale:
```
http://<tailscale-ip>/ca.mobileconfig
```

### Per Android
L'utente apre il browser e va a:
```
http://<server-ip>/ca.pem
```
Oppure tramite Tailscale:
```
http://<tailscale-ip>/ca.pem
```

Android può importare il certificato direttamente da:
- Impostazioni > Sicurezza > Certificati di autorità > Installa da storage
- Oppure tramite:
  - Impostazioni > Sicurezza > Crittografia > Certificati CA
  - Importa il file `.pem` scaricato

## Log del Server

All'avvio, il server ora mostra:
```
[ios-server] ready. Certificate profile for the phone: http://<ip>/ca.mobileconfig
[ios-server] Android certificate: http://<ip>/ca.pem
[ios-server] leaf certificate valid until YYYY-MM-DD
```

## Formato Certificato

- **iOS**: File `.pem` (formato testo) tramite profilo `.mobileconfig`
- **Android**: File `.pem` (formato testo) scaricabile direttamente

Entrambi usano lo stesso certificato radice CA, quindi iOS e Android possono connettersi allo stesso server offline senza avvertimenti di sicurezza.

## Validità Certificati

- **Root CA**: 10 anni (3650 giorni)
- **Leaf Certificate**: 397 giorni
- **Rinnovo automatico**: Quando restano 30 giorni prima della scadenza

## Sicurezza

Il certificato CA è limitato tramite "Name Constraints" per funzionare SOLO con:
- `gumi.sg`
- `exvius.com`

Anche se il client si fida del certificato, non può essere usato per impersonare altri siti.
