# EaglEs EyE User Manual

## What Is EaglEs EyE?

EaglEs EyE is a local, private AI-powered project intelligence platform
that runs entirely on your machine. Think of it as a **digital twin**
for your software project — it watches, mirrors, protects, and understands
your code so you can make better engineering decisions.

### Watch

EaglEs EyE observes your project folder — files, directories, structure.
It notices what changes, when, and how.

### Mirror

It preserves a durable record of your project state over time. Nothing
is lost — every observation becomes part of the permanent knowledge base.

### Protect

By maintaining a complete, evidence-backed history, EaglEs EyE helps you
understand the impact of changes, trace decisions, and detect drift
before it becomes a problem.

### Understand

EaglEs EyE extracts knowledge from your project: symbols, dependencies,
documentation, git history, architecture patterns. It builds a **Project
Twin** — a machine-readable representation of your entire project that
you can query, explore, and reason about.

## Main Capabilities

### Project Discovery

Point EaglEs EyE at any project folder. It automatically detects:

- **Project type**: Flutter, Python, Node.js, React, Java, Rust, Go, .NET, and more
- **Languages**: Dart, Python, JavaScript, TypeScript, Java, Rust, Go, C#, Kotlin, Swift, Ruby, PHP, YAML, JSON
- **Frameworks**: Flutter, React, Vue, Express, Next.js, Angular, Firebase, Node.js
- **Git repository**: Detects `.git` directory automatically
- **Dependencies**: Extracts from `pubspec.yaml`, `package.json`, `requirements.txt`

### Project Twin Creation

Once discovered, EaglEs EyE creates a **Project Twin** — a complete JSON
snapshot of your project's identity, stack, structure, and dependencies.
This twin is:

- **Stored** in `{memory_path}/twins/{project_name}.twin.json`
- **Indexed** in the knowledge store for search and retrieval
- **Notified** via the EventBus so other services can react

### Documentation Intelligence

EaglEs EyE scans your project's markdown files and documentation to
understand what each part of your system does. It links documentation
to code automatically.

### Semantic Memory

All observations, events, and extracted knowledge are stored in a durable
SQLite database. Nothing is ephemeral — you can search, query, and replay
your project history at any time.

### Knowledge Retrieval

Search your project's memory using full-text search, cross-reference
lookups, or vector similarity (if embeddings are enabled). Every result
includes citations back to the original source — no hidden reasoning.

## Creating Your First Twin

### Step 1: Start EaglEs EyE

```powershell
cd EaglEs-EyE
.venv\Scripts\Activate.ps1
python -m gui.app
```

Your browser opens automatically to **http://127.0.0.1:9103**.

### Step 2: Open the Help Page

Click **Help** in the top navigation bar. This page contains buttons
that guide you through the Twin creation workflow.

### Step 3: Connect a Project

Click **Connect Project**. Enter the full path to your project folder.

Examples:
- `C:\Users\me\projects\my-app`
- `/home/me/projects/my-app`

### Step 4: Scan the Project

Click **Scan Project**. EaglEs EyE analyses the folder:

- Lists all files (excluding hidden and build directories)
- Detects the project type, languages, and frameworks
- Checks for a Git repository
- Extracts dependencies from config files

### Step 5: Create the Twin

Click **Create Twin**. EaglEs EyE assembles everything into a Project Twin
and stores it in the knowledge base.

### Expected Notifications

As each stage completes, you will see these notifications:

```
CONNECTED
PROJECT IDENTIFIED
EYE SCAN
STACK DETECTED
GIT REPOSITORY DETECTED
DEPENDENCIES DISCOVERED
PROJECT TWIN CREATED
```

### What's Next?

Once your twin is created, explore it:

- **AI Twin tab**: View the twin overview, connectors, and reasoning
- **Search tab**: Search your project's symbols, events, and documents
- **Graph tab**: Explore symbol relationships and dependencies
- **Explain tab**: Ask questions about your project and get evidence-backed answers
