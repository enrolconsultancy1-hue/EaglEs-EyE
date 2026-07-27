# Project Twin Intelligence Workflow

```
          USER
           │
           ▼
       CONNECT
           │
           ▼
  PROJECT DISCOVERY
           │
           ▼
    FILE ANALYSIS
           │
           ▼
    CODE ANALYSIS
           │
           ▼
MARKDOWN DOCUMENT ANALYSIS
           │
           ▼
  DEPENDENCY ANALYSIS
           │
           ▼
     GIT ANALYSIS
           │
           ▼
 KNOWLEDGE EXTRACTION
           │
           ▼
 PROJECT TWIN CREATION
```

## Stage Details

### 1. USER

You provide the path to your project folder. EaglEs EyE does not scan
your entire filesystem — it only examines the directory you specify.

### 2. CONNECT

The LocalProjectConnector opens a connection to the project folder.
It verifies the path exists and is accessible. On success:

```
[CONNECTED] → EventBus: TWIN_CONNECTED
```

### 3. PROJECT DISCOVERY

The connector identifies the project type by looking for known marker files:

| Marker File | Project Type |
|---|---|
| `pubspec.yaml` + `lib/main.dart` | Flutter Application |
| `setup.py` / `pyproject.toml` / `requirements.txt` | Python Application |
| `package.json` | Node.js / React Application |
| `pom.xml` / `build.gradle` | Java / Kotlin Application |
| `Cargo.toml` | Rust Application |
| `go.mod` | Go Application |
| `*.csproj` / `*.sln` | .NET Application |

```
[PROJECT IDENTIFIED] → EventBus: TWIN_IDENTIFIED
```

### 4. FILE ANALYSIS

The connector walks the directory tree, counting files and mapping the
project structure. Hidden directories (`.git`, `.venv`, `node_modules`,
`build`, `.dart_tool`, `__pycache__`) are automatically excluded.

Language detection happens at this stage by file extension:

| Extension | Language |
|---|---|
| `.py` | Python |
| `.dart` | Dart |
| `.js`, `.jsx` | JavaScript |
| `.ts`, `.tsx` | TypeScript |
| `.java` | Java |
| `.rs` | Rust |
| `.go` | Go |
| `.cs` | C# |
| `.kt`, `.kts` | Kotlin |
| `.swift` | Swift |
| `.rb` | Ruby |
| `.php` | PHP |
| `.yaml`, `.yml` | YAML |
| `.json` | JSON |

### 5. CODE ANALYSIS

The connector looks inside key config files for framework detection:

- **pubspec.yaml**: Searches for `firebase` and `flutter` keywords
- **package.json**: Checks dependencies for React, Vue, Express, Next.js,
  Angular, Firebase

```
[STACK DETECTED] → EventBus: TWIN_STACK_DETECTED
```

### 6. MARKDOWN DOCUMENT ANALYSIS

Documentation files (`.md`, `.rst`) are indexed into the knowledge store
for documentation intelligence capabilities.

### 7. DEPENDENCY ANALYSIS

Dependencies are extracted from project config files:

| File | Extracted From |
|---|---|
| `pubspec.yaml` | Two-space-indented entries under `dependencies:` |
| `package.json` | `dependencies` and `devDependencies` objects |
| `requirements.txt` | Package names (one per line, no versions) |

### 8. GIT ANALYSIS

The connector checks for a `.git` subdirectory. If found, the repository
is flagged as `"detected": true` with type `"git"`.

```
[GIT REPOSITORY DETECTED] → EventBus: TWIN_GIT_DETECTED
```

### 9. KNOWLEDGE EXTRACTION

The collected data is normalized and recorded into the knowledge store:

- Event: `PROJECT_TWIN_DISCOVERED`
- Payload includes: project type, languages, frameworks, dependencies,
  file count, git status, and the full twin data

```
[DEPENDENCIES DISCOVERED] → EventBus: TWIN_DEPENDENCIES
```

### 10. PROJECT TWIN CREATION

The final twin is assembled and persisted:

1. Twin JSON is written atomically to `{memory_path}/twins/{name}.twin.json`
2. Knowledge is indexed via `KnowledgeStoreService.record_event()`
3. A final notification is published

```
[PROJECT TWIN CREATED] → EventBus: TWIN_CREATED
```

The twin JSON structure:

```json
{
  "project": {
    "name": "my-project",
    "path": "/path/to/my-project",
    "type": "Flutter Application",
    "languages": ["Dart", "YAML"],
    "frameworks": ["Flutter", "Firebase"]
  },
  "repository": {
    "type": "git",
    "detected": true
  },
  "dependencies": ["firebase_core", "cloud_firestore"],
  "statistics": {
    "file_count": 47
  },
  "discovery_time": "2026-07-26T12:00:00Z",
  "status": "CONNECTED"
}
```

## Total Pipeline

| Stage | Services Involved | Events Published |
|---|---|---|
| Connect | LocalProjectConnector | TWIN_CONNECTED |
| Scan | LocalProjectConnector | TWIN_SCAN |
| Identify | LocalProjectConnector | TWIN_IDENTIFIED |
| Stack Detect | LocalProjectConnector | TWIN_STACK_DETECTED |
| Git Detect | LocalProjectConnector | TWIN_GIT_DETECTED |
| Dependencies | LocalProjectConnector | TWIN_DEPENDENCIES |
| Twin Created | ProjectTwinDiscoveryService | TWIN_CREATED |
| Knowledge Index | KnowledgeStoreService | PROJECT_TWIN_DISCOVERED |
