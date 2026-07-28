"""ProjectIntelligenceEnhancer — post-processes connector discovery output to
improve classification, project type naming, architect summary, tech stack
extraction, architecture pattern detection, and purpose filtering.

Runs after the connector (frozen) but before twin storage.
Extends the v3.0.0 platform without modifying frozen components.
"""

import os


# Domain signal sets
REAL_ESTATE_KEYWORDS = {"property", "listing", "tenant", "landlord", "lease",
                        "building", "real estate", "realestate"}
ENTERPRISE_KEYWORDS = {"multi tenant", "multi-tenant", "rbac", "authentication",
                       "dashboard", "enterprise", "saas", "role based",
                       "role-based", "role based access"}

# Source priority weights (higher = more reliable)
SOURCE_WEIGHTS = {
    "architecture_doc": 4,
    "goal_doc": 3,
    "readme": 2,
    "roadmap_doc": 2,
    "framework": 2,
    "folder_structure": 2,
    "project_type": 1,
    "project_name": 1,
}

SIGNAL_TO_DOMAIN = {
    "mobile": "mobile_application",
    "web": "web_application",
    "backend": "backend_service",
    "ai": "ai_system",
    "enterprise": "enterprise_platform",
    "enterprise_platform": "enterprise_platform",
    "real_estate": "enterprise_platform",
}

# Architecture pattern signatures (canonical name mapping)
ARCH_PATTERN_SIGNATURES = {
    "clean architecture": "Clean Architecture",
    "feature-first": "Feature-first",
    "feature first": "Feature-first",
    "mvc": "MVC",
    "model-view-controller": "MVC",
    "mvvm": "MVVM",
    "model-view-viewmodel": "MVVM",
    "offline-first": "Offline-first",
    "offline first": "Offline-first",
    "bloc pattern": "BLoC Pattern",
    "provider": "Provider Pattern",
    "repository pattern": "Repository Pattern",
    "dependency injection": "Dependency Injection",
    "domain-driven design": "Domain-Driven Design",
    "event-driven": "Event-Driven Architecture",
    "microservice": "Microservices",
    "cqs": "CQS/CQRS",
    "cqrs": "CQS/CQRS",
}

# Generated / template / asset path patterns to ignore
GENERATED_PATH_PATTERNS = {
    "node_modules", ".dart_tool", "build", "dist", ".git", ".github",
    "coverage", "__pycache__", "generated", "template", "asset",
    "assets", ".pub-cache", ".gradle", ".idea", ".vscode",
    "cmake", "cmake-build", "cmake-build-debug", "cmake-build-release",
    ".cmake", "target",
}

# ---- Framework Tier Classification ----
# Primary: core application frameworks that define the project's identity
PRIMARY_TIER = {
    "flutter", "react", "react native", "vue", "angular", "svelte",
    "django", "flask", "fastapi", "express", "spring", "gin", "echo",
    "tensorflow", "pytorch", "keras", "next.js", "nuxt", "gatsby",
    "asp.net", "rails", "laravel", "symfony",
    "node.js", "deno", "bun",
}

# Secondary: libraries, packages, and services used by the application
SECONDARY_TIER = {
    "provider", "riverpod", "bloc", "redux", "mobx", "getx",
    "dio", "http", "graphql", "apollo",
    "sqflite", "hive", "isar", "objectbox", "floor", "shared_preferences",
    "flutter_svg", "cached_network_image", "shimmer", "lottie",
    "json_serializable", "freezed", "injectable", "get_it", "kiwi",
    "geolocator", "google_maps",
    "firebase", "supabase",
    "firebase_core", "cloud_firestore", "firebase_auth",
    "firebase_storage", "firebase_messaging",
    "firebase_analytics", "firebase_crashlytics",
    "sentry", "stripe", "algolia", "datadog",
    "mockito", "mocktail",
}

# Infrastructure: CI/CD, deployment, containerization, build tools
INFRA_TIER = {
    "docker", "kubernetes",
    "github actions", "gitlab ci/cd", "jenkins", "circleci",
    "make", "cmake",
    "pytest", "jest", "mocha", "junit",
    "pip", "npm", "yarn",
}

# Mapping from dependency / tier name to secondary category
SECONDARY_CATEGORY_MAP = {
    "provider": "state_management",
    "riverpod": "state_management",
    "bloc": "state_management",
    "redux": "state_management",
    "mobx": "state_management",
    "getx": "state_management",
    "dio": "networking",
    "http": "networking",
    "graphql": "networking",
    "apollo": "networking",
    "sqflite": "local_storage",
    "hive": "local_storage",
    "isar": "local_storage",
    "objectbox": "local_storage",
    "floor": "local_storage",
    "shared_preferences": "local_storage",
    "flutter_svg": "image_loading",
    "cached_network_image": "image_loading",
    "shimmer": "ui_toolkit",
    "lottie": "ui_toolkit",
    "json_serializable": "code_generation",
    "freezed": "code_generation",
    "injectable": "dependency_injection",
    "get_it": "dependency_injection",
    "kiwi": "dependency_injection",
    "geolocator": "device_service",
    "google_maps": "device_service",
    "firebase_core": "cloud_service",
    "cloud_firestore": "cloud_service",
    "firebase_auth": "cloud_service",
    "firebase_storage": "cloud_service",
    "firebase_messaging": "cloud_service",
    "firebase_analytics": "cloud_service",
    "firebase_crashlytics": "cloud_service",
    "supabase": "cloud_service",
    "firebase": "cloud_service",
    "sentry": "cloud_service",
    "stripe": "cloud_service",
    "algolia": "cloud_service",
    "datadog": "cloud_service",
    "mockito": "testing",
    "mocktail": "testing",
}

CATEGORY_LABELS = {
    "state_management": "State Management",
    "networking": "Networking",
    "local_storage": "Local Storage",
    "cloud_service": "Cloud Services",
    "device_service": "Device Services",
    "image_loading": "Image Loading",
    "ui_toolkit": "UI Toolkit",
    "code_generation": "Code Generation",
    "dependency_injection": "Dependency Injection",
    "testing": "Testing",
}

# Known dependency names that map to a framework/platform name + tier
DEP_TO_FRAMEWORK = {
    "flutter": ("Flutter", "primary"),
    "firebase_core": ("firebase_core", "secondary"),
    "cloud_firestore": ("cloud_firestore", "secondary"),
    "firebase_auth": ("firebase_auth", "secondary"),
    "firebase_storage": ("firebase_storage", "secondary"),
    "firebase_messaging": ("firebase_messaging", "secondary"),
    "firebase_analytics": ("firebase_analytics", "secondary"),
    "firebase_crashlytics": ("firebase_crashlytics", "secondary"),
    "provider": ("provider", "secondary"),
    "riverpod": ("riverpod", "secondary"),
    "bloc": ("bloc", "secondary"),
    "go_router": ("go_router", "secondary"),
    "react": ("React", "primary"),
    "express": ("Express", "primary"),
    "next": ("Next.js", "primary"),
    "django": ("Django", "primary"),
    "flask": ("Flask", "primary"),
    "fastapi": ("FastAPI", "primary"),
    "tensorflow": ("TensorFlow", "primary"),
    "torch": ("PyTorch", "primary"),
    "dio": ("dio", "secondary"),
    "sqflite": ("sqflite", "secondary"),
    "hive": ("hive", "secondary"),
    "get_it": ("get_it", "secondary"),
    "injectable": ("injectable", "secondary"),
    "freezed": ("freezed", "secondary"),
    "json_serializable": ("json_serializable", "secondary"),
    "geolocator": ("geolocator", "secondary"),
    "mockito": ("mockito", "secondary"),
    "mocktail": ("mocktail", "secondary"),
}

CLOUD_PLATFORM_NAMES = {"firebase", "supabase"}


# ---- Helpers ----

def _is_generated_path(path):
    """Check if a file path indicates generated, template, or asset content."""
    p = path.lower().replace("\\", "/")
    parts = set(p.split("/"))
    if parts & GENERATED_PATH_PATTERNS:
        return True
    for pat in GENERATED_PATH_PATTERNS:
        if pat in p:
            return True
    return False


def _gather_doc_content(doc_info):
    """Extract content from key doc files by role/path."""
    goal_content = ""
    roadmap_content = ""
    arch_content = ""
    for doc in doc_info.get("files") or []:
        path = doc.get("path", "").lower()
        preview = (doc.get("preview") or "").lower()
        if doc.get("role") == "architecture":
            arch_content = preview
        elif "goal" in path:
            goal_content = preview
        elif "roadmap" in path:
            roadmap_content = preview
    return goal_content, roadmap_content, arch_content


def _check_folder_signals(project_path):
    """Check folder structure for platform signals."""
    if not project_path or not os.path.isdir(project_path):
        return set()
    signals = set()
    has_lib = os.path.isdir(os.path.join(project_path, "lib"))
    has_android = os.path.isdir(os.path.join(project_path, "android"))
    has_ios = os.path.isdir(os.path.join(project_path, "ios"))
    if has_lib and (has_android or has_ios):
        signals.add("mobile")
    return signals


def _extract_domain_signals(text):
    """Extract domain signal keywords from text content.

    Uses specific keywords for each domain. Avoids false positives
    from common words like \"service\" in general documentation.
    """
    signals = set()
    if not text:
        return signals
    tl = text.lower()
    if any(kw in tl for kw in ("mobile", "android", "ios", "flutter")):
        signals.add("mobile")
    if any(kw in tl for kw in ("web", "browser", "frontend", "website")):
        signals.add("web")
    if any(kw in tl for kw in ("api", "rest", "microservice")):
        signals.add("backend")
    if any(kw in tl for kw in ("ml", "machine learning", "ai", "tensorflow", "neural")):
        signals.add("ai")
    for kw in REAL_ESTATE_KEYWORDS:
        if kw in tl:
            signals.add("real_estate")
            break
    for kw in ENTERPRISE_KEYWORDS:
        if kw in tl:
            signals.add("enterprise")
            break
    return signals


def _convert_evidence(evidence_list):
    """Convert evidence list items to (source, signal) tuples.

    Handles both dict format and tuple format for robustness.
    """
    result = []
    for item in evidence_list:
        if isinstance(item, dict):
            result.append((item.get("source", ""), item.get("signal", "")))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            result.append((item[0], item[1]))
    return result


def _framework_domain_signals(frameworks):
    """Map detected frameworks to domain signals."""
    signals = []
    fw_set = {f.lower() for f in frameworks}
    if fw_set & {"flutter", "react native", "kotlin", "swift"}:
        signals.append(("framework", "mobile"))
    if fw_set & {"react", "vue", "angular", "next.js", "svelte"}:
        signals.append(("framework", "web"))
    if fw_set & {"express", "django", "flask", "fastapi", "spring", "gin", "echo"}:
        signals.append(("framework", "backend"))
    if fw_set & {"tensorflow", "pytorch", "keras", "ml/ai"}:
        signals.append(("framework", "ai"))
    if fw_set & {"firebase", "supabase"}:
        signals.append(("framework", "enterprise"))
    return signals


# ---- 1. Technology Stack Extraction ----

def _classify_framework(fw_name):
    """Classify a framework name into (tier, normalized_name)."""
    lower = fw_name.lower()
    if lower in PRIMARY_TIER:
        return ("primary", fw_name)
    if lower in INFRA_TIER:
        return ("infra", fw_name)
    if lower in SECONDARY_TIER:
        return ("secondary", fw_name)
    return ("secondary", fw_name)


def _check_firebase_config(config_files):
    """Check config_files for Firebase configuration indicators."""
    firebase_signals = []
    for f in (config_files.get("files") or []):
        path = (f.get("path") or "").lower()
        if path == "firebase.json":
            firebase_signals.append("firebase.json")
        elif path == "firestore.rules":
            firebase_signals.append("firestore.rules")
        elif path.startswith("functions/"):
            firebase_signals.append("functions")
    return firebase_signals


def _classify_secondary(name):
    """Map a secondary framework name to its category.

    Returns (category_key, list_of_category_labels_for_item).
    """
    lower = name.lower()
    cat = SECONDARY_CATEGORY_MAP.get(lower, "other")
    return cat


def _categorize_secondary_items(items):
    """Group secondary framework names into categorized dicts.

    Returns [{"category": str, "libraries": [str]}, ...].
    """
    groups = {}
    for name in items:
        cat = _classify_secondary(name)
        label = CATEGORY_LABELS.get(cat, cat.replace("_", " ").title())
        fmt = name.replace("_", " ").title()
        if label not in groups:
            groups[label] = []
        groups[label].append(fmt)

    result = []
    for label in sorted(groups):
        result.append({
            "category": label,
            "libraries": sorted(set(groups[label])),
        })
    return result


def enhance_tech_stack(discovery_result):
    """Extract and rank technology stack from connector output.

    Uses three-tier classification:
      Primary   — core application frameworks (Flutter, React, Django, ...)
      Secondary — libraries and services (Provider, Firebase Auth, ...)
      Infra     — CI/CD, deployment, build tools (Docker, GitHub Actions, ...)

    Sources in priority order:
      1. Connector-detected frameworks (project.frameworks)
      2. Dependency list augmentation (dependencies)
      3. Config file analysis (firebase.json, etc.)

    Documentation content is NOT used for framework detection.
    """
    frameworks = discovery_result.get("project", {}).get("frameworks", [])
    dependencies = discovery_result.get("dependencies", [])
    config_files = discovery_result.get("config_files", {})
    doc_info = discovery_result.get("documentation", {})

    primary_set = set()
    secondary_set = set()
    infra_set = set()
    cloud_services = set()

    # ---- Source 1: Connector-detected frameworks ----
    for fw in frameworks:
        tier, norm = _classify_framework(fw)
        if tier == "primary":
            primary_set.add(norm)
        elif tier == "infra":
            infra_set.add(norm)
        elif tier == "secondary":
            lower = norm.lower()
            cat = _classify_secondary(norm)
            if cat == "cloud_service":
                # Secondary cloud items go to both cloud_services and secondary
                cloud_services.add(norm.title() if not lower.startswith("firebase_")
                                   else norm.replace("_", " ").title())
                if lower in CLOUD_PLATFORM_NAMES:
                    cloud_services.add(norm.title())
            secondary_set.add(norm)

    # ---- Source 2: Dependency list augmentation ----
    for dep in dependencies:
        lower = dep.lower()
        if lower in DEP_TO_FRAMEWORK:
            fw_name, tier = DEP_TO_FRAMEWORK[lower]
            if tier == "primary":
                if fw_name not in primary_set:
                    primary_set.add(fw_name)
            elif tier == "secondary":
                if fw_name not in secondary_set:
                    cat = _classify_secondary(fw_name)
                    if cat == "cloud_service":
                        cloud_services.add(fw_name.replace("_", " ").title()
                                           if "_" in fw_name else fw_name.title())
                    secondary_set.add(fw_name)

    # ---- Source 3: Firebase config detection ----
    firebase_signals = _check_firebase_config(config_files)
    if firebase_signals:
        cloud_services.add("Firebase")
        if "Firebase" not in secondary_set:
            secondary_set.add("Firebase")
            if "Firebase" not in primary_set:
                pass  # Firebase is secondary, not primary

    # ---- Build categorized secondary ----
    secondary_fws = _categorize_secondary_items(secondary_set)

    # ---- Architecture patterns (from doc content — this is about design, not frameworks) ----
    arch_patterns_set = set()
    for doc in doc_info.get("files") or []:
        if _is_generated_path(doc.get("path", "")):
            continue
        text = (doc.get("preview") or "").lower()
        for pattern_text, pattern_name in ARCH_PATTERN_SIGNATURES.items():
            if pattern_text in text:
                arch_patterns_set.add(pattern_name)

    pattern_order = ["Clean Architecture", "Feature-first", "MVC", "MVVM",
                     "Offline-first", "BLoC Pattern", "Provider Pattern",
                     "Repository Pattern", "Dependency Injection",
                     "Domain-Driven Design", "Event-Driven Architecture",
                     "Microservices", "CQS/CQRS"]
    sorted_patterns = []
    for p in pattern_order:
        if p in arch_patterns_set:
            sorted_patterns.append(p)
    for p in sorted(arch_patterns_set):
        if p not in sorted_patterns:
            sorted_patterns.append(p)

    return {
        "primary_frameworks": sorted(primary_set),
        "secondary_frameworks": secondary_fws,
        "infrastructure": sorted(infra_set),
        "cloud_services": sorted(cloud_services),
        "architecture_patterns": sorted_patterns,
    }


# ---- 2. Architecture Pattern Detection (enhanced) ----

def _extract_architecture_patterns(doc_info):
    """Extract architecture pattern references from all doc files.

    Scans every non-generated doc for pattern mentions including
    Clean Architecture, Feature-first, MVC, MVVM, Offline-first, etc.
    """
    patterns = []
    seen = set()
    for doc in doc_info.get("files") or []:
        if _is_generated_path(doc.get("path", "")):
            continue
        text = (doc.get("preview") or "").lower()
        for pattern_text, pattern_name in ARCH_PATTERN_SIGNATURES.items():
            if pattern_text in text and pattern_name not in seen:
                patterns.append(pattern_name)
                seen.add(pattern_name)
    return patterns


# ---- 3. Purpose Extraction Enhancement ----

def _filter_purpose_clues(purpose_clues, doc_info):
    """Filter and re-prioritize purpose clues.

    - Remove clues sourced from generated/template/assets/CMake paths
    - Prioritize architecture doc clues
    - Filter out Flutter generated README content
    - Rebuild summary from best available clue
    """
    if not purpose_clues:
        return purpose_clues

    filtered_clues = []
    arch_clues = []
    other_clues = []

    for clue in purpose_clues.get("clues", []):
        source = clue[0] if isinstance(clue, (list, tuple)) else clue.get("source", "")
        text = clue[1] if isinstance(clue, (list, tuple)) else clue.get("text", "")

        if hasattr(clue, "get"):
            path = clue.get("path", "")
        else:
            path = text if source == "architecture" else ""

        if _is_generated_path(path):
            continue

        if "cmake" in text.lower() or "cmake" in source.lower():
            continue

        lower_text = text.lower()
        if any(pat in lower_text for pat in ("generated", "template", "asset")):
            continue

        if "flutter" in source.lower() and "readme" in source.lower():
            continue

        if source == "architecture":
            arch_clues.append(clue)
        else:
            other_clues.append(clue)

    filtered_clues = arch_clues + other_clues

    new_summary = ""
    if arch_clues:
        arch_text = arch_clues[0][1] if isinstance(arch_clues[0], (list, tuple)) else arch_clues[0].get("text", "")
        new_summary = arch_text[:200]
    elif other_clues:
        other_text = other_clues[0][1] if isinstance(other_clues[0], (list, tuple)) else other_clues[0].get("text", "")
        new_summary = other_text[:200]
    else:
        new_summary = purpose_clues.get("summary", "")

    return {
        "clues": filtered_clues,
        "summary": new_summary,
        "details": purpose_clues.get("details", []),
    }


# ---- 4. Classification ----

def enhance_classification(discovery_result):
    """Enhance classification with additional signals from GOAL.md,
    ROADMAP.md, folder structure, direct framework analysis, and
    domain-specific keywords.

    Preserves existing connector evidence (converting to tuple format)
    and adds new evidence with source-priority weighting.
    """
    doc_info = discovery_result.get("documentation", {})
    classification = discovery_result.get("project", {}).get("classification", {})
    project_path = discovery_result.get("project", {}).get("path", "")
    frameworks = discovery_result.get("project", {}).get("frameworks", [])

    goal_content, roadmap_content, arch_content = _gather_doc_content(doc_info)
    folder_signals = _check_folder_signals(project_path)

    evidence = _convert_evidence(classification.get("evidence", []))

    def _add_evidence(src, signal):
        if (src, signal) not in evidence:
            evidence.append((src, signal))

    for src, signal in _framework_domain_signals(frameworks):
        _add_evidence(src, signal)

    ptype = discovery_result.get("project", {}).get("type", "")
    if "flutter" in ptype.lower():
        _add_evidence("project_type", "mobile")

    for sig in _extract_domain_signals(goal_content):
        _add_evidence("goal_doc", sig)
    for sig in _extract_domain_signals(roadmap_content):
        _add_evidence("roadmap_doc", sig)
    for sig in _extract_domain_signals(arch_content):
        _add_evidence("architecture_doc", sig)
    for sig in folder_signals:
        _add_evidence("folder_structure", sig)
    summary = doc_info.get("summary", "").lower() if doc_info else ""
    for sig in _extract_domain_signals(summary):
        _add_evidence("readme", sig)

    domain_scores = {
        "mobile_application": 0,
        "web_application": 0,
        "backend_service": 0,
        "ai_system": 0,
        "enterprise_platform": 0,
    }
    for src, signal in evidence:
        domain = SIGNAL_TO_DOMAIN.get(signal)
        if domain:
            domain_scores[domain] += SOURCE_WEIGHTS.get(src, 1)

    sorted_domains = sorted(domain_scores.items(), key=lambda x: -x[1])
    top_domain = sorted_domains[0][0]
    top_score = sorted_domains[0][1]
    runner_up = sorted_domains[1][1] if len(sorted_domains) > 1 else 0

    if top_score == 0:
        confidence = "low"
        domain_label = classification.get("domain", "general_application")
    elif top_score >= 5 and top_score > runner_up + 1:
        confidence = "high"
        domain_label = top_domain
    elif top_score >= 3 and top_score > runner_up:
        confidence = "medium"
        domain_label = top_domain
    elif top_score > 0:
        confidence = "low"
        domain_label = top_domain
    else:
        confidence = classification.get("confidence", "low")
        domain_label = classification.get("domain", "general_application")

    return {
        "domain": domain_label,
        "confidence": confidence,
        "evidence": [{"source": s, "signal": k} for s, k in evidence],
        "scores": domain_scores,
    }


# ---- 5. Project Type ----

def refine_project_type(original_type, classification, frameworks):
    """Return a descriptive project type name based on classification
    domain and detected technology stack.
    """
    domain = classification.get("domain", "")
    fw_set = {f.lower() for f in frameworks}
    dl = domain.lower()

    if dl == "mobile_application":
        if "flutter" in fw_set:
            return "Flutter Mobile Application"
        if "react native" in fw_set:
            return "React Native Mobile Application"
        return "Mobile Application"

    if dl == "enterprise_platform":
        if "flutter" in fw_set:
            return "Enterprise SaaS Platform"
        if any(f in fw_set for f in ("react", "vue", "angular")):
            return "Enterprise SaaS Platform"
        return "Enterprise Platform"

    if dl == "backend_service":
        return "Backend Service"

    if dl == "ai_system":
        return "AI System"

    if dl == "web_application":
        if "react" in fw_set:
            return "React Web Application"
        if "vue" in fw_set:
            return "Vue Web Application"
        if "angular" in fw_set:
            return "Angular Web Application"
        if "next.js" in fw_set:
            return "Next.js Web Application"
        return "Web Application"

    ot = original_type.lower()
    if "flutter" in ot:
        return "Flutter Mobile Application"
    if ot in ("unknown project", ""):
        return "Application"
    return original_type


# ---- 6. Architect Summary ----

def _extract_domain_purpose(doc_info):
    """Extract domain-specific purpose keywords from documents."""
    domain_terms = []
    summary = (doc_info.get("summary") or "").lower()
    for kw in REAL_ESTATE_KEYWORDS:
        if kw in summary:
            domain_terms.append(kw)
            break
    for doc in doc_info.get("files") or []:
        if _is_generated_path(doc.get("path", "")):
            continue
        text = (doc.get("preview") or "").lower()
        for kw in REAL_ESTATE_KEYWORDS:
            if kw in text and kw not in domain_terms:
                domain_terms.append(kw)
                break
        for kw in ENTERPRISE_KEYWORDS:
            if kw in text and kw not in domain_terms:
                domain_terms.append(kw.replace("_", " "))
                break
    return domain_terms


def generate_architect_summary(discovery_result, classification, refined_type):
    """Generate an architect-level project summary.

    Format: {Project Name} is a {descriptors} {type} for {purpose}.
    It uses {key_technologies} and {architecture_patterns}.
    """
    project_name = discovery_result.get("project", {}).get("name", "Project")
    doc_info = discovery_result.get("documentation", {})
    domain = classification.get("domain", "")
    frameworks = discovery_result.get("project", {}).get("frameworks", [])

    display_name = project_name.replace("_", " ").replace("-", " ").title()
    type_noun = refined_type.lower()
    fw_set = {f.lower() for f in frameworks}

    article = "an" if type_noun[0] in "aeiou" else "a"

    tech_tag = ""
    if "flutter" in fw_set and "flutter" not in type_noun:
        tech_tag = " (Flutter)"
    elif "react" in fw_set and "react" not in type_noun:
        tech_tag = " (React)"

    domain_terms = _extract_domain_purpose(doc_info)
    purpose_phrase = ""
    if domain_terms:
        clean_terms = [t for t in domain_terms if t not in type_noun]
        if clean_terms:
            purpose_phrase = " for " + " ".join(clean_terms) + " operations"

    s1 = f"{display_name} is {article} {type_noun}{tech_tag}{purpose_phrase}."

    service_refs = []
    if "firebase" in fw_set:
        service_refs.append("Firebase services")
    if "supabase" in fw_set:
        service_refs.append("Supabase")
    if "docker" in fw_set:
        service_refs.append("containerization (Docker)")

    patterns = _extract_architecture_patterns(doc_info)

    s2_parts = []
    if service_refs:
        s2_parts.append("uses " + ", ".join(service_refs))
    if patterns:
        s2_parts.append(", ".join(patterns))

    features = []
    summary = (doc_info.get("summary") or "").lower()
    for kw in ENTERPRISE_KEYWORDS:
        if kw in summary and kw.replace("_", " ") not in features:
            features.append(kw.replace("_", " "))
    for doc in doc_info.get("files") or []:
        if _is_generated_path(doc.get("path", "")):
            continue
        text = (doc.get("preview") or "").lower()
        for kw in ENTERPRISE_KEYWORDS:
            if kw in text and kw.replace("_", " ") not in features:
                features.append(kw.replace("_", " "))
    if features:
        combo = type_noun + " " + " ".join(s2_parts)
        f_clean = [f for f in features if f not in combo]
        if f_clean:
            s2_parts.append(", ".join(f_clean[:3]))

    s2 = ""
    if s2_parts:
        last = s2_parts.pop()
        if s2_parts:
            s2 = "It " + ", ".join(s2_parts) + ", and " + last + "."
        else:
            s2 = "It " + last + "."

    result = s1
    if s2:
        result += " " + s2
    return result


# ---- Pipeline ----

def enhance(discovery_result):
    """Full enhancement pipeline: classification, type naming, tech stack,
    purpose filtering, and architect summary.

    Returns the enhanced discovery_result (modified in place and returned).
    """
    if not discovery_result or not discovery_result.get("project"):
        return discovery_result

    original_type = discovery_result.get("project", {}).get("type", "Unknown")
    frameworks = discovery_result.get("project", {}).get("frameworks", [])

    enhanced_cls = enhance_classification(discovery_result)
    refined_type = refine_project_type(original_type, enhanced_cls, frameworks)
    tech_stack = enhance_tech_stack(discovery_result)
    purpose_clues = discovery_result.get("purpose_clues", {})
    filtered_purpose = _filter_purpose_clues(purpose_clues,
                                              discovery_result.get("documentation", {}))
    summary = generate_architect_summary(discovery_result, enhanced_cls, refined_type)

    discovery_result["project"]["classification"] = enhanced_cls
    discovery_result["project"]["type"] = refined_type
    discovery_result["tech_stack"] = tech_stack
    discovery_result["purpose_clues"] = filtered_purpose
    discovery_result["architect_summary"] = summary

    # Convert tech_stack to framework_tiers format consumed by the GUI
    fw_tiers = {
        "primary": tech_stack.get("primary_frameworks", [])[:],
        "secondary": [],
        "infrastructure": tech_stack.get("infrastructure", [])[:],
    }
    for sf in tech_stack.get("secondary_frameworks", []):
        for lib in sf.get("libraries", []):
            if lib not in fw_tiers["secondary"]:
                fw_tiers["secondary"].append(lib)
    for cs in tech_stack.get("cloud_services", []):
        if cs not in fw_tiers["secondary"] and cs not in fw_tiers["primary"]:
            fw_tiers["secondary"].append(cs)
    discovery_result["project"]["framework_tiers"] = fw_tiers

    return discovery_result
