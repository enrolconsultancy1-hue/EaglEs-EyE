"""CognitiveTwinService — phases cognitive knowledge from a discovered Project
Twin into structured dimensions (purpose, domain, architecture, maturity,
key components, risks, recommendations) and answers natural-language questions
about the project using deterministic reasoning over twin evidence.

No external LLM calls. Every answer is backed by cited evidence from the
Project Twin JSON, semantic knowledge, and documentation analysis.
"""

import json
import os
import time

from services.service import Service


# Risk severity weights
_SEVERITY_WEIGHTS = {"critical": 4, "high": 3, "medium": 2, "low": 1}

# Technology lifecycle signals for maturity detection
_TECH_LIFECYCLE = {
    "flutter": "active",
    "firebase": "active",
    "react": "active",
    "vue": "active",
    "angular": "active",
    "node.js": "active",
    "python": "active",
    "django": "active",
    "flask": "active",
    "fastapi": "active",
    "tensorflow": "active",
    "pytorch": "active",
    "docker": "active",
    "kubernetes": "active",
    "angularjs": "declining",
    "jquery": "legacy",
    "bower": "archived",
}

# Domain-specific architecture pattern expectations
_DOMAIN_ARCH_PATTERNS = {
    "mobile_application": ["MVVM", "BLoC Pattern", "Provider Pattern", "Clean Architecture", "Repository Pattern"],
    "web_application": ["MVC", "MVVM", "Clean Architecture", "Feature-first"],
    "backend_service": ["Microservices", "Event-Driven Architecture", "Clean Architecture", "Repository Pattern"],
    "enterprise_platform": ["Clean Architecture", "Domain-Driven Design", "Microservices", "Event-Driven Architecture"],
    "ai_system": ["Pipeline Architecture", "Clean Architecture", "Microservices"],
}

# Component significance scoring — which doc/role indicates what kind of component
_COMPONENT_ROLE_MAP = {
    "architecture": "core_architecture",
    "readme": "documentation",
    "changelog": "history",
    "contributing": "community",
    "goal": "strategy",
    "roadmap": "strategy",
}


def _utc_iso():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _safe_get(d, *keys, default=""):
    """Safely traverse nested dicts."""
    for k in keys:
        if isinstance(d, dict):
            d = d.get(k)
        else:
            return default
    return d if d is not None else default


class CognitiveTwinService(Service):
    """Phases cognitive knowledge from a Project Twin and answers
    deterministic questions about project purpose, domain, architecture,
    maturity, risks, and recommendations."""

    def __init__(self, kernel):
        super().__init__(kernel)
        self.store = None
        self.code_intelligence = None
        self._twin_cache = {}

    def start(self):
        super().start()
        self.store = self.kernel.get_service("KnowledgeStoreService")
        try:
            self.code_intelligence = self.kernel.get_service("CodeIntelligenceService")
        except Exception:
            self.code_intelligence = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_twin(self, twin_data):
        """Load a Project Twin dict into the cognitive engine.

        Returns a cognitive summary dict structured into the seven
        cognitive knowledge dimensions.
        """
        if not twin_data or not isinstance(twin_data, dict):
            return {"error": "No twin data provided"}
        fp = twin_data.get("fingerprint", twin_data.get("project", {}).get("name", "unknown"))
        cognition = self._generate_cognition(twin_data)
        self._twin_cache[fp] = {
            "twin": twin_data,
            "cognition": cognition,
            "loaded_at": _utc_iso(),
        }
        return cognition

    def load_twin_from_path(self, twin_path):
        """Load a Project Twin from its JSON file path."""
        if not os.path.isfile(twin_path):
            return {"error": f"Twin file not found: {twin_path}"}
        with open(twin_path, encoding="utf-8") as f:
            twin_data = json.load(f)
        return self.load_twin(twin_data)

    def has_twin(self, fingerprint=None):
        """Check if a twin is loaded. Returns True/False."""
        if fingerprint:
            return fingerprint in self._twin_cache
        return bool(self._twin_cache)

    def get_cognition(self, fingerprint=None):
        """Retrieve the most recent or specified cognitive summary."""
        if fingerprint and fingerprint in self._twin_cache:
            return self._twin_cache[fingerprint]["cognition"]
        if self._twin_cache:
            last = list(self._twin_cache.values())[-1]
            return last["cognition"]
        return {"error": "No twin loaded"}

    def ask(self, question):
        """Answer a natural-language question about the loaded project twin.

        Uses only deterministic reasoning over twin evidence.
        Returns {"answer": str, "evidence": list, "confidence": str}.
        """
        if not self._twin_cache:
            return {"answer": "No project twin loaded. Discover a project first.", "evidence": [], "confidence": "none"}
        last = list(self._twin_cache.values())[-1]
        twin = last["twin"]
        cognition = last["cognition"]

        q = question.lower().strip()

        # Route question to the appropriate handler
        if any(kw in q for kw in ("what is this", "explain", "describe", "overview", "summary", "about")):
            return self._answer_overview(twin, cognition)
        if any(kw in q for kw in ("purpose", "what does it do", "what is it for", "goal", "mission")):
            return self._answer_purpose(twin, cognition)
        if any(kw in q for kw in ("domain", "category", "classification", "type of")):
            return self._answer_domain(twin, cognition)
        if any(kw in q for kw in ("architecture", "structure", "pattern", "design")):
            return self._answer_architecture(twin, cognition)
        if any(kw in q for kw in ("mature", "maturity", "stable", "production")):
            return self._answer_maturity(twin, cognition)
        if any(kw in q for kw in ("component", "module", "part", "file", "source")):
            return self._answer_components(twin, cognition)
        if any(kw in q for kw in ("risk", "danger", "problem", "concern", "vulnerability")):
            return self._answer_risks(twin, cognition)
        if any(kw in q for kw in ("recommend", "suggest", "improve", "next step", "what next")):
            return self._answer_recommendations(twin, cognition)
        if any(kw in q for kw in ("tech", "stack", "framework", "language", "dependency")):
            return self._answer_tech(twin, cognition)
        if any(kw in q for kw in ("team", "size", "scale", "large", "big", "complexity")):
            return self._answer_scale(twin, cognition)
        if any(kw in q for kw in ("code intelligence", "code analysis", "code structure", "programming language")):
            return self._answer_code(twin, cognition)

        # Fallback: provide the summary
        summary = cognition.get("purpose", {}).get("summary", cognition.get("architect_summary", ""))
        if summary:
            return {
                "answer": summary,
                "evidence": [{"type": "cognition", "source": "cognitive_twin", "detail": "fallback to project summary"}],
                "confidence": "medium",
            }
        return {"answer": "I do not understand the question. Try: explain, purpose, domain, architecture, maturity, components, risks, recommendations, tech, or team.", "evidence": [], "confidence": "none"}

    # ------------------------------------------------------------------
    # Cognitive knowledge generation
    # ------------------------------------------------------------------

    def _generate_cognition(self, twin):
        """Generate all cognitive knowledge dimensions from twin data."""
        purpose = self._analyze_purpose(twin)
        domain = self._analyze_domain(twin)
        architecture = self._analyze_architecture(twin)
        maturity = self._analyze_maturity(twin)
        key_components = self._analyze_key_components(twin)
        risks = self._analyze_risks(twin)
        code_summary = self._analyze_code(twin)
        cognition = {
            "purpose": purpose,
            "domain": domain,
            "architecture": architecture,
            "maturity": maturity,
            "key_components": key_components,
            "risks": risks,
            "recommendations": self._generate_recommendations(twin, {
                "purpose": purpose,
                "domain": domain,
                "architecture": architecture,
                "maturity": maturity,
                "key_components": key_components,
                "risks": risks,
            }),
            "code_summary": code_summary,
        }
        return cognition

    def _generate_cognition_skip_recommendations(self, twin):
        """Generate cognition without recommendations to break recursion."""
        return {
            "purpose": self._analyze_purpose(twin),
            "domain": self._analyze_domain(twin),
            "architecture": self._analyze_architecture(twin),
            "maturity": self._analyze_maturity(twin),
            "key_components": self._analyze_key_components(twin),
            "risks": self._analyze_risks(twin),
            "code_summary": self._analyze_code(twin),
        }

    # ---- 1. Purpose ----

    def _analyze_purpose(self, twin):
        """Extract project purpose from architect_summary, purpose_clues, README."""
        purpose_clues = twin.get("purpose_clues", {})
        arch_summary = twin.get("architect_summary", "")
        doc_summary = ""
        docs = twin.get("documentation", {})
        for f in docs.get("files", []):
            if "readme" in f.get("role", "").lower() or "readme" in f.get("path", "").lower():
                doc_summary = f.get("preview", "")[:300]
                break
        clues = purpose_clues.get("clues", [])
        clue_text = " ".join(c[1] if isinstance(c, (list, tuple)) and len(c) > 1 else "" for c in clues) if clues else ""

        summary = ""
        if arch_summary:
            summary = arch_summary[:300]
        elif purpose_clues.get("summary"):
            summary = purpose_clues["summary"][:300]
        elif doc_summary:
            summary = doc_summary[:300]
        elif clue_text:
            summary = clue_text[:300]

        return {
            "summary": summary,
            "has_summary": bool(summary),
            "source_count": len(clues),
            "primary_source": purpose_clues.get("details", [{}])[0] if purpose_clues.get("details") else {},
        }

    # ---- 2. Domain ----

    def _analyze_domain(self, twin):
        """Analyze project domain from classification and evidence."""
        proj = twin.get("project", {})
        classification = proj.get("classification", {})
        domain = classification.get("domain", "unknown")
        confidence = classification.get("confidence", "low")
        evidence = classification.get("evidence", [])

        domain_labels = {
            "mobile_application": "Mobile Application",
            "web_application": "Web Application",
            "backend_service": "Backend Service",
            "ai_system": "AI / Machine Learning System",
            "enterprise_platform": "Enterprise Platform",
            "general_application": "General Application",
        }

        return {
            "domain": domain,
            "label": domain_labels.get(domain, domain.replace("_", " ").title()),
            "confidence": confidence,
            "evidence_count": len(evidence),
            "evidence_sources": list({e.get("source", "") for e in evidence}),
            "scores": classification.get("scores", {}),
        }

    # ---- 3. Architecture ----

    def _analyze_architecture(self, twin):
        """Analyze architecture patterns, style, and documentation."""
        proj = twin.get("project", {})
        tech_stack = twin.get("tech_stack", {})
        doc_cats = twin.get("documentation_categories", {})

        arch_docs = [d.get("path", "") for d in doc_cats.get("architecture", [])]
        patterns = tech_stack.get("architecture_patterns", [])
        primary = proj.get("framework_tiers", {}).get("primary", [])
        domain = proj.get("classification", {}).get("domain", "")

        arch_description = ""
        if patterns:
            arch_description = "Architecture patterns: " + ", ".join(patterns) + "."
        if primary:
            arch_description += " Core frameworks: " + ", ".join(primary) + "."
        if not arch_description:
            arch_description = "No explicit architecture patterns detected."

        expected = _DOMAIN_ARCH_PATTERNS.get(domain, [])
        matched = [p for p in patterns if p in expected]
        missing = [p for p in expected if p not in patterns]

        return {
            "description": arch_description,
            "patterns": patterns,
            "pattern_count": len(patterns),
            "documentation_count": len(arch_docs),
            "documentation_files": arch_docs[:10],
            "domain_expected_patterns": expected,
            "domain_matched_patterns": matched,
            "domain_missing_patterns": missing,
        }

    # ---- 4. Maturity ----

    def _analyze_maturity(self, twin):
        """Assess project maturity from documentation, dependencies, and tech lifecycle."""
        docs = twin.get("documentation", {})
        doc_files = docs.get("files", [])
        dep_list = twin.get("dependencies", [])
        proj = twin.get("project", {})
        frameworks = [f.lower() for f in proj.get("frameworks", [])]
        stats = twin.get("statistics", {})
        has_git = twin.get("repository", {}).get("detected", False)

        signals = []

        # Documentation completeness
        doc_count = len(doc_files)
        has_arch = any("architecture" in (d.get("role") or "").lower() or "architecture" in (d.get("path") or "").lower() for d in doc_files)
        has_changelog = any("changelog" in (d.get("role") or "").lower() or "changelog" in (d.get("path") or "").lower() for d in doc_files)
        has_readme = any("readme" in (d.get("role") or "").lower() or "readme" in (d.get("path") or "").lower() for d in doc_files)

        if doc_count >= 5:
            signals.append(("positive", "comprehensive_documentation"))
        elif doc_count >= 3:
            signals.append(("positive", "moderate_documentation"))
        else:
            signals.append(("concern", "sparse_documentation"))

        if has_arch:
            signals.append(("positive", "architecture_documentation"))
        if has_changelog:
            signals.append(("positive", "changelog_present"))
        if has_readme:
            signals.append(("positive", "readme_present"))
        if has_git:
            signals.append(("positive", "version_control_detected"))

        # Technology lifecycle
        lifecycle_scores = []
        for fw in frameworks:
            lc = _TECH_LIFECYCLE.get(fw, "unknown")
            if lc == "active":
                lifecycle_scores.append(1)
            elif lc == "declining":
                lifecycle_scores.append(-1)
                signals.append(("concern", f"declining_technology:{fw}"))
            elif lc == "legacy":
                lifecycle_scores.append(-2)
                signals.append(("risk", f"legacy_technology:{fw}"))
            elif lc == "archived":
                lifecycle_scores.append(-3)
                signals.append(("risk", f"archived_technology:{fw}"))
        avg_lifecycle = sum(lifecycle_scores) / max(len(lifecycle_scores), 1)

        # Dependency quality
        dep_count = len(dep_list)
        if dep_count > 20:
            signals.append(("concern", "large_dependency_count"))
        elif dep_count > 10:
            signals.append(("note", "moderate_dependency_count"))

        # File-based growth signal
        file_count = stats.get("file_count", 0)
        if file_count > 200:
            signals.append(("positive", "substantial_codebase"))
        elif file_count > 50:
            signals.append(("positive", "moderate_codebase"))
        elif file_count > 10:
            signals.append(("note", "small_codebase"))

        # Compute composite maturity score (0.0 to 1.0)
        score = 0.3  # baseline
        if doc_count >= 5:
            score += 0.15
        elif doc_count >= 3:
            score += 0.1
        if has_arch:
            score += 0.1
        if has_changelog:
            score += 0.05
        if has_readme:
            score += 0.05
        if has_git:
            score += 0.1
        if avg_lifecycle > 0:
            score += 0.1
        elif avg_lifecycle < 0:
            score -= 0.1
        if dep_count > 20:
            score -= 0.05
        if file_count > 200:
            score += 0.1
        score = max(0.0, min(1.0, score))

        level = "initial"
        if score >= 0.8:
            level = "mature"
        elif score >= 0.6:
            level = "established"
        elif score >= 0.4:
            level = "developing"
        elif score >= 0.2:
            level = "early"

        return {
            "level": level,
            "score": round(score, 2),
            "signals": [{"type": t, "signal": s} for t, s in signals],
            "signal_count": len(signals),
            "documentation_count": doc_count,
            "version_control": has_git,
        }

    # ---- 5. Key Components ----

    def _analyze_key_components(self, twin):
        """Identify key project components from file structure and documentation roles."""
        doc_cats = twin.get("documentation_categories", {})
        doc_files = twin.get("documentation", {}).get("files", [])
        config_files = twin.get("config_files", {}).get("files", [])
        proj = twin.get("project", {})

        components = []

        # Documentation-based components
        for role_name, cat_list in doc_cats.items():
            role_label = role_name.replace("_", " ").title()
            if cat_list:
                components.append({
                    "name": role_label,
                    "category": _COMPONENT_ROLE_MAP.get(role_name, "documentation"),
                    "count": len(cat_list),
                    "files": [d.get("path", "") for d in cat_list[:5]],
                    "source": "documentation_category",
                })

        # Config-based components
        ci_configs = [f for f in config_files if f.get("purpose") == "ci"]
        docker_configs = [f for f in config_files if f.get("purpose") == "docker"]
        build_configs = [f for f in config_files if f.get("purpose") == "build"]

        if ci_configs:
            components.append({
                "name": "CI/CD Pipeline",
                "category": "infrastructure",
                "count": len(ci_configs),
                "files": [f.get("path", "") for f in ci_configs[:3]],
                "source": "config_analysis",
            })
        if docker_configs:
            components.append({
                "name": "Containerization",
                "category": "infrastructure",
                "count": len(docker_configs),
                "files": [f.get("path", "") for f in docker_configs[:3]],
                "source": "config_analysis",
            })
        if build_configs:
            components.append({
                "name": "Build System",
                "category": "infrastructure",
                "count": len(build_configs),
                "files": [f.get("path", "") for f in build_configs[:3]],
                "source": "config_analysis",
            })

        # Framework-based components
        fw_tiers = proj.get("framework_tiers", {})
        for tier_name in ("primary", "secondary", "infrastructure"):
            items = fw_tiers.get(tier_name, [])
            if items:
                components.append({
                    "name": tier_name.title() + " Technologies",
                    "category": "technology",
                    "count": len(items),
                    "items": items[:10],
                    "source": "framework_tiers",
                })

        # Dependency-based components
        deps = twin.get("dependencies", [])
        if deps:
            components.append({
                "name": "Dependencies",
                "category": "technology",
                "count": len(deps),
                "items": deps[:15],
                "source": "dependency_analysis",
            })

        return {
            "components": components,
            "component_count": len(components),
            "has_infrastructure": any(c["category"] == "infrastructure" for c in components),
            "has_documentation": any(c["category"] == "documentation" for c in components),
        }

    # ---- 6. Risks ----

    def _analyze_risks(self, twin):
        """Detect project risks from twin evidence."""
        risks = []
        docs = twin.get("documentation", {})
        doc_files = docs.get("files", [])
        dep_list = twin.get("dependencies", [])
        proj = twin.get("project", {})
        frameworks = [f.lower() for f in proj.get("frameworks", [])]
        classification = proj.get("classification", {})
        stats = twin.get("statistics", {})
        has_git = twin.get("repository", {}).get("detected", False)

        # Risk: no version control
        if not has_git:
            risks.append({
                "risk": "No version control detected",
                "severity": "high",
                "detail": "Project is not tracked in Git. Risk of unrecoverable changes.",
                "category": "governance",
            })

        # Risk: sparse or missing documentation
        doc_count = len(doc_files)
        if doc_count < 2:
            risks.append({
                "risk": "Insufficient documentation",
                "severity": "high",
                "detail": f"Only {doc_count} documentation file(s) found. This impacts maintainability and onboarding.",
                "category": "documentation",
            })
        elif doc_count < 4:
            has_arch = any("architecture" in (d.get("role") or d.get("path", "")).lower() for d in doc_files)
            if not has_arch:
                risks.append({
                    "risk": "Missing architecture documentation",
                    "severity": "medium",
                    "detail": "No architecture-specific documentation found. Architectural decisions may be undocumented.",
                    "category": "architecture",
                })

        # Risk: deprecated or archived technologies
        for fw in frameworks:
            lc = _TECH_LIFECYCLE.get(fw)
            if lc in ("legacy", "archived"):
                risks.append({
                    "risk": f"Legacy technology: {fw.title()}",
                    "severity": "high",
                    "detail": f"{fw.title()} is {lc}. Consider migration to a supported alternative.",
                    "category": "technology_risk",
                })
            elif lc == "declining":
                risks.append({
                    "risk": f"Declining technology: {fw.title()}",
                    "severity": "medium",
                    "detail": f"{fw.title()} shows declining community adoption. Plan for eventual migration.",
                    "category": "technology_risk",
                })

        # Risk: large dependency footprint
        dep_count = len(dep_list)
        if dep_count > 30:
            risks.append({
                "risk": "Large dependency footprint",
                "severity": "medium",
                "detail": f"{dep_count} dependencies detected. Increases vulnerability surface and build complexity.",
                "category": "dependency_management",
            })
        elif dep_count > 50:
            risks.append({
                "risk": "Very large dependency footprint",
                "severity": "high",
                "detail": f"{dep_count} dependencies detected. Significant vulnerability surface and potential supply chain risk.",
                "category": "dependency_management",
            })

        # Risk: low classification confidence
        conf = classification.get("confidence", "")
        if conf == "low":
            risks.append({
                "risk": "Low domain classification confidence",
                "severity": "medium",
                "detail": "The project domain could not be determined with high confidence. Consider adding explicit documentation.",
                "category": "clarity",
            })

        # Risk: missing README
        has_readme = any("readme" in (d.get("role") or d.get("path", "")).lower() for d in doc_files)
        if not has_readme:
            risks.append({
                "risk": "No README found",
                "severity": "high",
                "detail": "A README is essential for onboarding and project understanding.",
                "category": "documentation",
            })

        # Risk: no changelog
        has_changelog = any("changelog" in (d.get("role") or d.get("path", "")).lower() for d in doc_files)
        if not has_changelog:
            risks.append({
                "risk": "No changelog found",
                "severity": "low",
                "detail": "Without a changelog, tracking version history and feature releases is harder.",
                "category": "documentation",
            })

        # Sort by severity
        severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        risks.sort(key=lambda r: severity_order.get(r["severity"], 99))

        return {
            "risks": risks,
            "risk_count": len(risks),
            "high_severity_count": sum(1 for r in risks if r["severity"] in ("critical", "high")),
            "categories": list({r["category"] for r in risks}),
        }

    # ---- 7. Code Summary ----

    def _analyze_code(self, twin):
        """Generate code intelligence summary from project path."""
        if not self.code_intelligence:
            return {
                "languages": [], "components": [],
                "architecture_layers": [], "complexity": "",
                "entry_points": [], "important_files": [],
            }
        project_path = twin.get("project", {}).get("path", "")
        if not project_path or not os.path.isdir(project_path):
            return {
                "languages": [], "components": [],
                "architecture_layers": [], "complexity": "",
                "entry_points": [], "important_files": [],
                "error": "Project path not available or not accessible",
            }
        return self.code_intelligence.analyze_project(project_path)

    # ---- 8. Recommendations ----

    def _generate_recommendations(self, twin, cognition=None):
        """Generate evidence-backed recommendations for project improvement."""
        recommendations = []
        if cognition is None:
            cognition = self._generate_cognition_skip_recommendations(twin)

        purpose = cognition.get("purpose", {})
        domain_data = cognition.get("domain", {})
        arch_data = cognition.get("architecture", {})
        maturity_data = cognition.get("maturity", {})
        risks_data = cognition.get("risks", {})
        components = cognition.get("key_components", {})

        # Recommendation: fill purpose gap
        if not purpose.get("has_summary"):
            recommendations.append({
                "recommendation": "Define a clear project purpose statement",
                "priority": "high",
                "rationale": "No explicit project purpose or architect summary found. This makes onboarding and decision-making harder.",
                "evidence": ["purpose_clues", "architect_summary"],
                "category": "documentation",
            })

        # Recommendation: improve documentation
        doc_files = twin.get("documentation", {}).get("files", [])
        has_arch_doc = any(
            "architecture" in (d.get("role") or d.get("path", "")).lower()
            for d in doc_files
        )
        if not has_arch_doc:
            recommendations.append({
                "recommendation": "Add architecture documentation",
                "priority": "high",
                "rationale": "Architecture documentation is missing. Documenting the system architecture improves maintainability and team onboarding.",
                "evidence": ["documentation_files", "architecture_analysis"],
                "category": "documentation",
            })

        # Recommendation: add missing architecture patterns
        missing_patterns = arch_data.get("domain_missing_patterns", [])
        if missing_patterns:
            recommendations.append({
                "recommendation": "Consider adopting domain-appropriate architecture patterns",
                "priority": "medium",
                "rationale": f"For {domain_data.get('label', 'this domain')}, common patterns include: {', '.join(missing_patterns)}.",
                "evidence": ["architecture_analysis", "domain_classification"],
                "category": "architecture",
            })

        # Recommendation: technology risk mitigation
        for risk in risks_data.get("risks", []):
            cat = risk.get("category", "")
            if cat == "technology_risk":
                recommendations.append({
                    "recommendation": f"Mitigate technology risk: {risk.get('risk', '')}",
                    "priority": risk.get("severity", "medium"),
                    "rationale": risk.get("detail", ""),
                    "evidence": ["risk_analysis", "technology_detection"],
                    "category": "technology_risk",
                })

        # Recommendation: missing README
        has_readme = any("readme" in (d.get("role") or d.get("path", "")).lower() for d in doc_files)
        if not has_readme:
            recommendations.append({
                "recommendation": "Create a comprehensive README",
                "priority": "high",
                "rationale": "A README is essential for project onboarding, documentation, and collaboration.",
                "evidence": ["documentation_files"],
                "category": "documentation",
            })

        # Recommendation: dependency audit
        dep_list = twin.get("dependencies", [])
        if len(dep_list) > 30:
            recommendations.append({
                "recommendation": "Audit dependency footprint",
                "priority": "medium",
                "rationale": f"{len(dep_list)} dependencies is substantial. Review for unused or redundant packages to reduce attack surface.",
                "evidence": ["dependency_analysis"],
                "category": "dependency_management",
            })

        # Recommendation: add CI/CD
        config_files = twin.get("config_files", {}).get("files", [])
        has_ci = any(f.get("purpose") == "ci" for f in config_files)
        if not has_ci:
            recommendations.append({
                "recommendation": "Set up CI/CD pipeline",
                "priority": "high",
                "rationale": "No CI/CD configuration detected. Automated testing and deployment are essential for code quality.",
                "evidence": ["config_analysis"],
                "category": "infrastructure",
            })

        # Recommendation: version control
        has_git = twin.get("repository", {}).get("detected", False)
        if not has_git:
            recommendations.append({
                "recommendation": "Initialize version control with Git",
                "priority": "critical",
                "rationale": "No Git repository detected. Version control is fundamental for collaboration, history tracking, and disaster recovery.",
                "evidence": ["repository_detection"],
                "category": "governance",
            })

        # Sort by priority
        priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
        recommendations.sort(key=lambda r: priority_order.get(r.get("priority", "medium"), 99))

        return {
            "recommendations": recommendations,
            "recommendation_count": len(recommendations),
            "high_priority_count": sum(1 for r in recommendations if r.get("priority") in ("critical", "high")),
            "categories": list({r["category"] for r in recommendations}),
        }

    # ------------------------------------------------------------------
    # Question handlers
    # ------------------------------------------------------------------

    def _answer_overview(self, twin, cognition):
        """Provide a comprehensive project overview."""
        proj = twin.get("project", {})
        arch_summary = twin.get("architect_summary", "")
        purpose = cognition.get("purpose", {})
        domain_data = cognition.get("domain", {})
        maturity_data = cognition.get("maturity", {})
        arch_data = cognition.get("architecture", {})
        components = cognition.get("key_components", {})

        parts = []
        if arch_summary:
            parts.append(arch_summary)
        else:
            name = proj.get("name", "Unknown")
            ptype = proj.get("type", "Unknown")
            domain_label = domain_data.get("label", "Unknown")
            parts.append(f"{name} is a {ptype} categorized as {domain_label}.")

        lang_list = proj.get("languages", [])
        fw_list = proj.get("frameworks", [])
        if lang_list or fw_list:
            parts.append(f"Languages: {', '.join(lang_list)}. Technologies: {', '.join(fw_list)}.")

        stat = twin.get("statistics", {})
        fc = stat.get("file_count", 0)
        dc = len(twin.get("dependencies", []))
        parts.append(f"Codebase: {fc} files, {dc} dependencies.")

        parts.append(f"Maturity: {maturity_data.get('level', 'unknown').title()}.")
        parts.append(f"Architecture patterns: {', '.join(arch_data.get('patterns', ['none detected']))}.")

        evidence = [
            {"type": "twin", "source": "architect_summary", "detail": "project summary"},
            {"type": "twin", "source": "project_identity", "detail": "name, type, languages, frameworks"},
            {"type": "cognition", "source": "maturity_analysis", "detail": maturity_data.get("level", "")},
            {"type": "cognition", "source": "architecture_analysis", "detail": str(arch_data.get("patterns", []))},
        ]

        return {
            "answer": " ".join(parts),
            "evidence": evidence,
            "confidence": "high",
        }

    def _answer_purpose(self, twin, cognition):
        """Answer questions about project purpose."""
        purpose = cognition.get("purpose", {})
        summary = purpose.get("summary", "")
        arch_summary = twin.get("architect_summary", "")
        proj = twin.get("project", {})

        answer = summary or arch_summary or f"The purpose of {proj.get('name', 'this project')} could not be determined from available documentation."

        evidence = [
            {"type": "twin", "source": "purpose_clues", "detail": "project purpose evidence"},
            {"type": "cognition", "source": "purpose_analysis", "detail": str(purpose.get("source_count", 0)) + " clue(s)"},
        ]

        return {
            "answer": answer,
            "evidence": evidence,
            "confidence": "high" if purpose.get("has_summary") else "medium",
        }

    def _answer_domain(self, twin, cognition):
        """Answer questions about project domain classification."""
        domain_data = cognition.get("domain", {})
        classification = twin.get("project", {}).get("classification", {})

        dc = domain_data.get("domain", "unknown")
        confidence = domain_data.get("confidence", "low")
        evidence_list = classification.get("evidence", [])

        answer = f"This project is classified as {domain_data.get('label', dc)} with {confidence} confidence."

        source_list = domain_data.get("evidence_sources", [])
        if source_list:
            answer += f" Evidence sources: {', '.join(source_list)}."

        evidence = [
            {"type": "twin", "source": "classification", "detail": f"domain={dc}, confidence={confidence}"},
            {"type": "twin", "source": "classification_evidence", "detail": str(len(evidence_list)) + " evidence items"},
        ]

        return {
            "answer": answer,
            "evidence": evidence,
            "confidence": confidence,
        }

    def _answer_architecture(self, twin, cognition):
        """Answer questions about project architecture."""
        arch_data = cognition.get("architecture", {})

        patterns = arch_data.get("patterns", [])
        docs = arch_data.get("documentation_files", [])

        parts = []
        if patterns:
            parts.append(f"Architecture patterns detected: {', '.join(patterns)}.")
        else:
            parts.append("No explicit architecture patterns detected from documentation.")

        if docs:
            parts.append(f"Architecture documentation ({arch_data.get('documentation_count', 0)} files):")
            for d in docs[:5]:
                parts.append(f"  - {d}")
        else:
            parts.append("No architecture documentation found.")

        evidence = [
            {"type": "cognition", "source": "architecture_analysis", "detail": str(patterns)},
            {"type": "twin", "source": "documentation_categories", "detail": str(arch_data.get("documentation_count", 0)) + " files"},
        ]

        return {
            "answer": "\n".join(parts),
            "evidence": evidence,
            "confidence": "high" if patterns else "medium",
        }

    def _answer_maturity(self, twin, cognition):
        """Answer questions about project maturity."""
        maturity_data = cognition.get("maturity", {})
        level = maturity_data.get("level", "unknown")
        score = maturity_data.get("score", 0)

        descriptions = {
            "mature": "This project appears mature with comprehensive documentation, version control, and established technology choices.",
            "established": "This project is established with moderate documentation and clear technology choices. Some areas could be strengthened.",
            "developing": "This project is still developing. Core documentation may be present but the project is still evolving.",
            "early": "This project is in early stages. Limited documentation and structure suggest it is actively being built.",
            "initial": "This project appears to be in its initial phase. Limited evidence of maturity indicators.",
        }

        answer = descriptions.get(level, f"Project maturity level: {level} (score: {score}).")

        signals = maturity_data.get("signals", [])
        if signals:
            pos = [s["signal"] for s in signals if s["type"] == "positive"]
            concerns = [s["signal"] for s in signals if s["type"] in ("concern", "risk")]
            if pos:
                answer += f" Strengths: {', '.join(pos[:5])}."
            if concerns:
                answer += f" Concerns: {', '.join(concerns[:5])}."

        evidence = [
            {"type": "cognition", "source": "maturity_analysis", "detail": f"level={level}, score={score}"},
            {"type": "cognition", "source": "maturity_signals", "detail": str(maturity_data.get("signal_count", 0)) + " signals"},
        ]

        return {
            "answer": answer,
            "evidence": evidence,
            "confidence": "high" if maturity_data.get("signal_count", 0) > 3 else "medium",
        }

    def _answer_components(self, twin, cognition):
        """Answer questions about project key components."""
        components = cognition.get("key_components", {})

        comp_list = components.get("components", [])
        if not comp_list:
            return {"answer": "No components could be identified from the twin data.", "evidence": [], "confidence": "low"}

        parts = [f"The project has {components.get('component_count', 0)} identified component groups:"]
        for comp in comp_list[:8]:
            name = comp.get("name", "Unknown")
            category = comp.get("category", "")
            count = comp.get("count", 0)
            parts.append(f"- {name} ({category}, {count} item(s))")

        evidence = [
            {"type": "cognition", "source": "component_analysis", "detail": str(components.get("component_count", 0)) + " groups"},
        ]

        return {
            "answer": "\n".join(parts),
            "evidence": evidence,
            "confidence": "high" if comp_list else "medium",
        }

    def _answer_risks(self, twin, cognition):
        """Answer questions about project risks."""
        risks_data = cognition.get("risks", {})

        risk_list = risks_data.get("risks", [])
        if not risk_list:
            return {"answer": "No significant risks detected from available evidence.", "evidence": [], "confidence": "medium"}

        parts = [f"Identified {risks_data.get('risk_count', 0)} risk(s) across {len(risks_data.get('categories', []))} category(ies):"]
        for r in risk_list:
            parts.append(f"[{r.get('severity', 'unknown').upper()}] {r.get('risk', '')}")
            parts.append(f"  {r.get('detail', '')}")

        evidence = [
            {"type": "cognition", "source": "risk_analysis", "detail": str(risks_data.get("risk_count", 0)) + " risks"},
        ]

        return {
            "answer": "\n".join(parts),
            "evidence": evidence,
            "confidence": "high",
        }

    def _answer_recommendations(self, twin, cognition):
        """Answer questions about project recommendations."""
        recommendations_data = cognition.get("recommendations", {})

        rec_list = recommendations_data.get("recommendations", [])
        if not rec_list:
            return {"answer": "No recommendations available. The project appears well-structured.", "evidence": [], "confidence": "medium"}

        parts = [f"Generated {recommendations_data.get('recommendation_count', 0)} recommendation(s):"]
        for r in rec_list[:10]:
            parts.append(f"[{r.get('priority', 'medium').upper()}] {r.get('recommendation', '')}")
            parts.append(f"  Rationale: {r.get('rationale', '')}")

        evidence = [
            {"type": "cognition", "source": "recommendation_analysis", "detail": str(recommendations_data.get("recommendation_count", 0)) + " recommendations"},
        ]

        return {
            "answer": "\n".join(parts),
            "evidence": evidence,
            "confidence": "high",
        }

    def _answer_tech(self, twin, cognition):
        """Answer questions about the technology stack."""
        proj = twin.get("project", {})
        frameworks = proj.get("frameworks", [])
        languages = proj.get("languages", [])
        dep_list = twin.get("dependencies", [])
        fw_tiers = proj.get("framework_tiers", {})

        parts = []
        if languages:
            parts.append(f"Languages: {', '.join(languages)}.")
        if fw_tiers:
            primary = fw_tiers.get("primary", [])
            if primary:
                parts.append(f"Primary: {', '.join(primary)}.")
            infra = fw_tiers.get("infrastructure", [])
            if infra:
                parts.append(f"Infrastructure: {', '.join(infra)}.")
        if dep_list:
            parts.append(f"Dependencies ({len(dep_list)} total).")

        evidence = [
            {"type": "twin", "source": "project_identity", "detail": f"languages={languages}, frameworks={frameworks}"},
            {"type": "twin", "source": "dependency_analysis", "detail": f"{len(dep_list)} deps"},
        ]

        return {
            "answer": " ".join(parts) if parts else "No technology information available.",
            "evidence": evidence,
            "confidence": "high" if languages or frameworks else "low",
        }

    def _answer_code(self, twin, cognition):
        """Answer code intelligence questions."""
        code = cognition.get("code_summary", {})
        if "error" in code:
            return {
                "answer": "Code analysis not available: " + code["error"],
                "evidence": [],
                "confidence": "none",
            }
        if self.code_intelligence and self.code_intelligence.has_analysis():
            return self.code_intelligence.code_query("overview")
        langs = code.get("languages", [])
        comps = code.get("components", [])
        layers = code.get("architecture_layers", [])
        complexity = code.get("complexity", "unknown")
        parts = ["Code Intelligence Summary:"]
        if langs:
            parts.append(f"Languages: {', '.join(l['name'] for l in langs)}.")
        parts.append(f"Classes/Interfaces: {len(comps)}. Complexity: {complexity}.")
        if layers:
            parts.append(f"Layers: {', '.join(l['layer'] for l in layers)}.")
        evidence = [
            {"type": "cognition", "source": "code_analysis",
             "detail": f"{len(langs)} lang(s), {len(comps)} class(es)"},
        ]
        return {"answer": " ".join(parts), "evidence": evidence, "confidence": "high"}

    def _answer_scale(self, twin, cognition):
        """Answer questions about project scale and complexity."""
        stats = twin.get("statistics", {})
        dep_list = twin.get("dependencies", [])
        doc_files = twin.get("documentation", {}).get("files", [])
        proj = twin.get("project", {})

        fc = stats.get("file_count", 0)
        dc = len(dep_list)
        doc_count = len(doc_files)
        lang_count = len(proj.get("languages", []))
        fw_count = len(proj.get("frameworks", []))

        parts = [f"File count: {fc}. Languages: {lang_count}. Technologies: {fw_count}. Dependencies: {dc}. Documentation files: {doc_count}."]

        if fc > 500:
            parts.append("This is a large-scale project.")
        elif fc > 100:
            parts.append("This is a medium-scale project.")
        else:
            parts.append("This is a small-scale project.")

        evidence = [
            {"type": "twin", "source": "statistics", "detail": f"files={fc}, deps={dc}, docs={doc_count}"},
        ]

        return {
            "answer": " ".join(parts),
            "evidence": evidence,
            "confidence": "high",
        }
