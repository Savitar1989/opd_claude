# Restaurant Delivery Bot - Moduláris verzió

## Projekt struktúra

```
project/
├── main.py                 # Fő indító fájl
├── requirements.txt        # Python függőségek
├── config/
│   └── settings.py         # Konfigurációs beállítások
├── database/
│   └── db_manager.py       # Adatbázis kezelő osztály
├── utils/
│   ├── address_parser.py   # Magyar cím feldolgozó
│   ├── geocoding.py        # Geokódolás és útvonal optimalizálás
│   └── url_shortener.py    # URL rövidítő
├── telegram_bot/
│   └── bot.py             # Telegram bot logika
└── web_app/
    ├── app.py             # Flask alkalmazás
    ├── routes/
    │   ├── api_routes.py  # API végpontok
    │   └── admin_routes.py # Admin funkcionalitás
    └── templates/
        └── templates.py   # HTML sablonok
```

## Telepítés és futtatás

1. **Függőségek telepítése:**
```bash
pip install -r requirements.txt
```

2. **Konfiguráció beállítása:**
   - Szerkeszd a `config/settings.py` fájlt
   - Állítsd be a `BOT_TOKEN`-t
   - Módosítsd a `WEBAPP_URL`-t (ngrok URL)
   - Add hozzá az admin user ID-kat

3. **Alkalmazás indítása:**
```bash
python main.py
```

## Modulok részletei

### config/settings.py
- Bot token és webapp URL
- Admin jogosultságok
- Logging beállítások
- Globális változók (notification queue)

### database/db_manager.py
- SQLite adatbázis kezelés
- Rendelések CRUD műveletek
- Statisztikai lekérdezések
- Automatikus migráció

### utils/address_parser.py
- Magyar címek normalizálása
- Rövidítések feloldása
- Irányítószám kezelés

### utils/geocoding.py
- OpenStreetMap Nominatim API
- Koordináták lekérése
- Haversine távolságszámítás
- Útvonal optimalizálás (nearest neighbor)

### telegram_bot/bot.py
- Telegram bot eseménykezelő
- Parancsok (start, help, register)
- Csoportüzenetek feldolgozása
- Értesítési rendszer

### web_app/app.py
- Flask alkalmazás inicializálás
- Blueprint regisztráció
- Főoldal route

### web_app/routes/api_routes.py
- REST API végpontok
- Rendelés elfogadás/felvétel/kiszállítás
- Telegram adatok validálása
- Útvonal optimalizálás API

### web_app/routes/admin_routes.py
- Admin statisztika oldal
- Jogosultság ellenőrzés
- Heti/napi jelentések

## Előnyök a moduláris struktúrának

1. **Könnyebb karbantartás**: Egy funkció módosítása nem érinti a többit
2. **Tiszta felelősségi körök**: Minden modul egyért felel
3. **Jobb tesztelhetőség**: Modulok külön-külön tesztelhetők
4. **Csapatmunka**: Többen dolgozhatnak párhuzamosan
5. **Újrafelhasználhatóság**: Modulok más projektekben is használhatók

## Fejlesztési tippek

- Új funkciók hozzáadásakor először döntsd el, melyik modulba tartozik
- Import-okat mindig a fájl tetején helyezd el
- Logging-ot minden modulban használj
- Hibakezelést minden külső API hívásnál alkalmazz
- Adatbázis módosításoknál gondolj a migrációra

## Telepítési különlegességek

- ngrok futtatása szükséges a webhook-hoz
- SQLite adatbázis automatikusan létrejön
- Webhook URL beállítása a Telegram Bot API-n keresztül