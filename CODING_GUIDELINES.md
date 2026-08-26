# IRON — Coding Guidelines

## 1. Scopo del documento

Questo file definisce le regole tecniche e organizzative da seguire durante lo sviluppo di IRON.

Serve come riferimento stabile per sviluppo manuale, pair programming, utilizzo di Codex e code review.

L'obiettivo è mantenere il progetto:
- comprensibile;
- modulare;
- estendibile;
- testabile;
- didatticamente utile;
- presentabile in un portfolio professionale.

## 2. Visione del progetto

IRON è un Adaptive Training Planner / Decision Support System per atleti con uno o più obiettivi contemporanei.

Non è una semplice dashboard fitness e non è un chatbot che decide autonomamente cosa deve fare l'utente.

IRON deve:
- raccogliere dati da più sorgenti;
- normalizzarli;
- analizzare storico, recupero, disponibilità e obiettivi;
- mantenere un piano settimanale;
- proporre più alternative di allenamento;
- spiegare vantaggi e compromessi di ogni alternativa;
- adattare il resto della settimana quando cambia una sessione;
- permettere all'utente di proporre una propria alternativa da valutare.

L'utente mantiene sempre il controllo finale.

## 3. Principi architetturali

### 3.1 Separation of Concerns

Ogni modulo deve avere una responsabilità chiara.

Separare almeno:
- **UI** → interazione con l'utente;
- **business logic** → regole applicative;
- **database/persistence** → salvataggio e lettura dati;
- **data ingestion** → import da sorgenti esterne;
- **feature engineering** → trasformazione dei dati;
- **decision engine** → ranking e valutazione degli scenari;
- **simulation engine** → valutazione delle conseguenze;
- **ML layer** → modelli predittivi futuri.

Evitare che un singolo file faccia tutto.

### 3.2 Dipendenze direzionali

La UI può chiamare i servizi.  
I servizi possono chiamare il database.  
Il database non deve conoscere la UI.  
Il Decision Engine non deve dipendere da Streamlit.

Esempio corretto:

```text
Streamlit UI
    ↓
Service Layer
    ↓
Database
```

Esempio da evitare:

```text
database.py
    ↓
st.success(...)
```

### 3.3 Semplicità prima dell'astrazione

Non introdurre microservizi, repository pattern, dependency injection complessa, message broker, code generator o framework non necessari finché il problema reale non lo richiede.

Preferire una soluzione semplice e leggibile che possa essere rifattorizzata in seguito.

## 4. Struttura del progetto

La struttura deve crescere progressivamente.

Struttura iniziale indicativa:

```text
IRON/
├── app/
│   ├── main.py
│   ├── database.py
│   └── workout_service.py
├── tests/
├── .gitignore
├── README.md
├── CODING_GUIDELINES.md
└── requirements.txt
```

Quando il progetto crescerà, potranno essere introdotti moduli dedicati come:

```text
app/
├── models/
├── services/
├── repositories/
├── integrations/
├── features/
├── decision_engine/
└── simulation/
```

Non creare cartelle vuote solo per anticipare una futura architettura.

## 5. Regole Python

### 5.1 Naming

Seguire PEP 8.

Usare `snake_case` per funzioni, variabili e moduli.  
Usare `PascalCase` per classi e modelli.  
Usare `UPPER_SNAKE_CASE` per costanti.

Esempio:

```python
SUPPORTED_SPORTS = ("Run", "Bike", "Swim", "Gym")

def calculate_training_load():
    ...

class Workout:
    ...
```

### 5.2 Nomi descrittivi

Preferire:

```python
weekly_training_load
```

a:

```python
wtl
```

Preferire:

```python
workout_date
```

a:

```python
d
```

La leggibilità è più importante del risparmio di caratteri.

### 5.3 Type hints

Usare type hints nelle funzioni non banali.

```python
def calculate_training_load(duration: int, rpe: int) -> int:
    return duration * rpe
```

I type hints aiutano leggibilità, IDE, refactoring, testing e comprensione del codice.

### 5.4 Funzioni piccole

Ogni funzione dovrebbe svolgere una responsabilità precisa.

Se una funzione valida, salva, calcola, formatta e mostra UI, probabilmente deve essere divisa.

### 5.5 Commenti

Non commentare codice ovvio.

Usare commenti per spiegare:
- il perché di una decisione;
- una limitazione;
- un comportamento non ovvio;
- una formula;
- un workaround.

### 5.6 Docstring

Usare docstring per funzioni e classi quando la responsabilità non è ovvia o quando fanno parte di un modulo riutilizzabile.

Preferire docstring concise.

## 6. Database

### 6.1 Obiettivo

Il database interno di IRON deve rappresentare i dati in modo indipendente dalle sorgenti esterne.

Non modellare il database copiando direttamente Strava o Garmin.

Flusso desiderato:

```text
Strava / Garmin / FIT
        ↓
Normalization
        ↓
IRON internal schema
```

### 6.2 Modelli comuni e specifici per sport

I campi comuni devono stare nel modello generale `Workout`.

Esempi:
- id;
- date;
- sport;
- duration;
- rpe;
- notes;
- source.

I dati specifici devono vivere in modelli dedicati.

Per la palestra prevedere in futuro:

```text
Workout
    ↓
Exercise
    ↓
Set
```

Evitare una singola tabella con decine di colonne quasi sempre `NULL`.

### 6.3 Primary key e foreign key

Ogni tabella principale deve avere una primary key.

Le relazioni tra entità devono usare foreign key esplicite e riflettere il dominio reale.

### 6.4 Dati derivabili

Non salvare dati facilmente derivabili senza una motivazione.

Esempio:

```text
pace = duration / distance
```

Se può essere calcolato in modo affidabile, non è necessario duplicarlo nel database.

### 6.5 Database locale

Durante l'MVP:
- SQLite è accettabile;
- il file del database locale non va versionato;
- aggiungerlo a `.gitignore`.

In futuro sarà possibile passare a PostgreSQL.

### 6.6 Migration

Finché il progetto è in fase iniziale e non contiene dati importanti, è accettabile ricreare il database durante modifiche di schema.

Quando IRON inizierà a contenere dati reali o multiutente, introdurre migration formali.

Non cancellare database o dati senza avvisare esplicitamente.

## 7. Service Layer

La business logic deve vivere nei service, non nella UI.

Esempio:

```text
main.py
    ↓
workout_service.py
    ↓
database.py
```

Il service deve gestire validazione, regole applicative, orchestrazione e chiamate alla persistenza.

La UI deve limitarsi principalmente a raccogliere input, chiamare servizi e mostrare output/errori.

## 8. Validazione

Non fidarsi della sola validazione della UI.

Anche se un `selectbox` consente solo determinati sport, il service deve comunque verificare che lo sport ricevuto sia valido.

La business validation deve restare valida anche se in futuro la stessa funzione viene chiamata da API, mobile app, test o import automatico.

## 9. Data ingestion e integrazioni

Le integrazioni esterne devono essere isolate.

Esempio:

```text
integrations/
├── strava.py
├── garmin.py
└── fit_parser.py
```

Ogni integrazione deve:
1. leggere i dati esterni;
2. convertirli nel modello interno IRON;
3. evitare che il resto dell'app dipenda dal formato del provider.

Non disseminare logica specifica Strava/Garmin in tutto il progetto.

## 10. Decision Engine

Il Decision Engine è il cuore del progetto.

Deve essere indipendente dalla UI e dalle sorgenti dati.

Input possibili:
- piano attuale;
- storico;
- readiness;
- disponibilità temporale;
- obiettivi;
- preferenze;
- vincoli.

Output:
- scenari;
- ranking;
- punteggi;
- motivazioni;
- conseguenze previste.

### 10.1 Explainability

Ogni decisione deve poter essere spiegata.

Evitare output come:

```text
Score = 82
```

senza spiegazione.

Preferire:

```text
+ buona continuità aerobica
+ tempo disponibile compatibile
- recupero inferiore alla media
- seduta gambe intensa nelle ultime 24 ore
```

### 10.2 Human in the Loop

IRON non deve impedire all'utente di scegliere un allenamento differente.

Deve invece poter:
- valutare l'alternativa;
- mostrarne costi e benefici;
- adattare il resto della pianificazione.

## 11. Machine Learning

Non introdurre ML finché:
- non esiste un dataset utilizzabile;
- non esiste una baseline rule-based;
- non è chiaro quale problema predittivo risolvere.

Il ML deve sostituire o migliorare una componente misurabile, non essere aggiunto solo per rendere il progetto "AI".

### 11.1 Baseline prima del modello

Ogni modello ML deve essere confrontato con una baseline semplice.

Esempio:

```text
Rule Engine
vs
Random Forest
vs
XGBoost
```

### 11.2 Population model e personalizzazione

In futuro IRON potrà utilizzare:
- un modello globale basato su più utenti;
- personalizzazione sul singolo atleta.

Tenere conto del cold-start problem.

Preferire feature relative al baseline personale quando appropriato.

### 11.3 LLM

Un LLM non deve essere il Decision Engine.

Flusso preferito:

```text
User input
    ↓
Decision Engine
    ↓
Structured result
    ↓
LLM opzionale
    ↓
Natural-language explanation
```

L'LLM può spiegare o interpretare, ma la logica core deve rimanere verificabile.

## 12. Testing

Aggiungere test quando introduciamo logica rilevante.

Priorità:
1. business logic;
2. Decision Engine;
3. trasformazioni dati;
4. parser;
5. database;
6. edge case.

Non è necessario testare ogni riga di UI Streamlit.

I test devono essere piccoli, deterministici, leggibili e indipendenti quando possibile.

Ogni bug importante corretto dovrebbe idealmente produrre un test che impedisca la regressione.

## 13. Git

### 13.1 Commit piccoli

Ogni commit deve rappresentare una modifica coerente.

Evitare:

```text
update stuff
```

Preferire:

```text
feat: add workout history
fix: validate workout duration
refactor: separate workout persistence logic
docs: update project architecture
```

### 13.2 Conventional Commits

Usare quando appropriato:

```text
feat:
fix:
docs:
test:
refactor:
chore:
```

### 13.3 Prima del commit

Controllare:

```bash
git status
git diff
```

Capire cosa viene committato.

Non fare commit di codice generato dall'AI senza averlo revisionato.

## 14. Dipendenze

Non aggiungere una nuova libreria se la standard library è sufficiente, una dipendenza esistente risolve già il problema o il beneficio è marginale.

Ogni nuova dipendenza deve avere una motivazione.

Aggiornare `requirements.txt` quando vengono aggiunte o rimosse dipendenze.

## 15. Sicurezza

Mai salvare nel repository:
- password;
- token;
- API key;
- secret;
- credenziali database.

Usare `.env` o sistemi di secrets.

`.env` deve essere presente in `.gitignore`.

Quando necessario creare `.env.example` con nomi delle variabili ma senza valori sensibili.

## 16. Logging ed error handling

Non ignorare silenziosamente gli errori.

Gli errori devono:
- essere intercettati al livello corretto;
- produrre messaggi utili;
- non esporre segreti.

Durante lo sviluppo usare logging sufficiente per capire cosa accade.

## 17. README e documentazione

Alla fine di ogni milestone importante aggiornare il README.

Il README deve spiegare:
- cosa fa IRON;
- architettura;
- come installarlo;
- come avviarlo;
- funzionalità presenti;
- roadmap;
- decisioni tecniche importanti.

Documentare anche il **perché**, non solo il cosa.

## 18. Regole specifiche per Codex

Codex è uno strumento di implementazione, non il proprietario dell'architettura.

### 18.1 Prima di modificare

Per task non banali deve:
1. leggere il codice rilevante;
2. spiegare quali file intende modificare;
3. spiegare sinteticamente l'approccio;
4. evidenziare eventuali rischi o cambiamenti di schema.

Se il prompt richiede conferma, deve attendere prima di modificare.

### 18.2 Task piccoli

Preferire modifiche piccole e verificabili.

Evitare di implementare più feature non richieste nello stesso task.

Non trasformare:

> "aggiungi la lettura degli allenamenti"

in:

> "rifaccio tutta l'architettura, aggiungo FastAPI e PostgreSQL".

### 18.3 No overengineering

Non introdurre pattern, framework o astrazioni senza necessità concreta.

La leggibilità per uno sviluppatore junior è un requisito del progetto.

### 18.4 Non modificare codice non correlato

Codex non deve rinominare file, spostare cartelle, cambiare formattazione globale, sostituire librerie o fare refactoring estesi se non è necessario per il task richiesto.

### 18.5 Approccio didattico

IRON è anche un progetto di apprendimento.

Il codice deve essere comprensibile, idiomatico e spiegabile.

Preferire una soluzione leggermente più esplicita ma didatticamente chiara rispetto a una soluzione molto compatta e difficile da capire.

### 18.6 Dopo la modifica

Codex deve fornire:
- elenco dei file modificati;
- riassunto delle modifiche;
- eventuali decisioni tecniche;
- come verificare il risultato;
- test eseguiti o da eseguire;
- eventuali limitazioni rimaste.

### 18.7 Test

Quando possibile, dopo una modifica:
- eseguire i test rilevanti;
- verificare import/sintassi;
- segnalare chiaramente se qualcosa non è stato testato.

### 18.8 Non nascondere problemi

Se una richiesta richiede modifica distruttiva del database, nuova dipendenza, cambio architetturale importante o compromesso tecnico rilevante, Codex deve dirlo prima di procedere.

## 19. Regola generale per le decisioni tecniche

Prima di aggiungere qualcosa chiedersi:

1. Quale problema risolve?
2. È necessario adesso?
3. Esiste una soluzione più semplice?
4. Aumenta significativamente la complessità?
5. È coerente con la visione di IRON?
6. È comprensibile e testabile?
7. Ci insegna qualcosa di utile?

Se non esiste una buona risposta, probabilmente non serve ancora.

## 20. Filosofia finale

IRON deve crescere progressivamente:

```text
semplice
    ↓
funzionante
    ↓
testato
    ↓
modulare
    ↓
scalabile
    ↓
intelligente
```

Non nell'ordine inverso.

Ogni versione deve essere utilizzabile e comprensibile prima di aggiungere la complessità della versione successiva.
