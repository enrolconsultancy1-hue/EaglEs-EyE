"""TwinReasoningService — explains project changes with architect-level reasoning.

Takes twin comparison results and produces:
- Human-readable explanations (what changed, why, impact, risk)
- Evolution insights per version transition
- Risk detection (dependency growth, missing docs, architecture drift, etc.)

Extends the v3.0.0 platform without modifying frozen components.
"""

from services.service import Service


# Known technology categories for risk detection
DEPRECATED_TECHS = {
    "angularjs", "angular.js", "jquery", "bower", "grunt", "gulp",
    "prototype.js", "backbone.js", "ember.js", "coffeescript",
    "moment.js", "underscore.js", "yeoman",
}


class TwinReasoningService(Service):
    """Explains project changes with evidence-backed architect-level reasoning."""

    def __init__(self, kernel):
        super().__init__(kernel)

    # --- 1. Change Reasoner ---

    def reason_change(self, comparison, old_twin=None, new_twin=None):
        """Produce human-readable explanation from a comparison result.

        Returns dict with: what_changed, likely_reason, architectural_impact,
        risk_indicators, explanation (combined narrative).
        """
        parts = []
        what = []
        why = []
        impact = []
        risks = []

        if not comparison.get("has_changes"):
            return {
                "what_changed": "No significant changes detected.",
                "likely_reason": "",
                "architectural_impact": "None.",
                "risk_indicators": [],
                "explanation": "No significant changes detected between versions.",
                "maturity_assessment": "",
            }

        # --- What changed ---
        new_files = comparison.get("new_files", [])
        removed_files = comparison.get("removed_files", [])
        deps_added = comparison.get("changed_dependencies", {}).get("added", [])
        deps_removed = comparison.get("changed_dependencies", {}).get("removed", [])
        fws_added = comparison.get("changed_frameworks", {}).get("added", [])
        fws_removed = comparison.get("changed_frameworks", {}).get("removed", [])
        docs_added = comparison.get("documentation_changes", {}).get("added", [])
        cls_changed = comparison.get("classification_changed", False)
        purpose_changed = comparison.get("purpose_changed", False)

        change_items = []
        if new_files:
            change_items.append(f"{len(new_files)} new file(s)")
        if removed_files:
            change_items.append(f"{len(removed_files)} removed file(s)")
        if deps_added:
            change_items.append(f"new dependencies ({', '.join(deps_added[:3])})")
        if deps_removed:
            change_items.append(f"removed dependencies ({', '.join(deps_removed[:3])})")
        if fws_added:
            change_items.append(f"new framework(s): {', '.join(fws_added)}")
        if fws_removed:
            change_items.append(f"removed framework(s): {', '.join(fws_removed)}")
        if docs_added:
            change_items.append(f"new documentation: {', '.join(docs_added)}")
        if cls_changed:
            change_items.append("domain reclassification")

        if change_items:
            what = f"The project experienced {', '.join(change_items)}."
            parts.append(what)

        # --- Why it likely changed ---
        why_parts = []
        if deps_added:
            why_parts.append(
                f"New dependencies ({', '.join(deps_added[:3])}) suggest feature expansion "
                "or integration with external services."
            )
        if fws_added:
            fw_whys = []
            for fw in fws_added:
                if fw.lower() in ("firebase", "supabase"):
                    fw_whys.append(f"{fw} indicates backend-as-a-service integration for authentication, database, or hosting")
                elif fw.lower() in ("docker", "kubernetes", "helm"):
                    fw_whys.append(f"{fw} adoption points to containerization and deployment pipeline improvements")
                elif fw.lower() in ("react", "vue", "angular"):
                    fw_whys.append(f"{fw} adoption signals a frontend framework migration or modernisation")
                elif fw.lower() in ("tensorflow", "pytorch", "keras"):
                    fw_whys.append(f"{fw} introduction indicates AI/ML capability expansion")
                else:
                    fw_whys.append(f"{fw} added — likely driven by new feature requirements")
            why_parts.extend(fw_whys)

        if removed_files:
            why_parts.append(
                f"{len(removed_files)} file(s) removed — likely cleanup, refactoring, "
                "or feature deprecation."
            )
        if docs_added:
            why_parts.append("Documentation added — improved project maintainability and onboarding.")
        if cls_changed:
            why_parts.append("Domain reclassification indicates a shift in project purpose or scope.")

        if why_parts:
            likely_reason = " ".join(why_parts)
            parts.append(likely_reason)

        # --- Architectural impact ---
        impact_parts = []
        if fws_added:
            impact_parts.append(f"Architecture complexity increased: {len(fws_added)} new framework(s) added to the stack.")
        if deps_added:
            impact_parts.append(f"Dependency graph expanded by {len(deps_added)} — may affect build time and vulnerability surface.")
        if new_files:
            impact_parts.append(f"Codebase grew by {len(new_files)} file(s).")
        if removed_files:
            impact_parts.append(f"Codebase reduced by {len(removed_files)} file(s) — potential simplification or deletion.")
        if fws_removed:
            impact_parts.append(f"Framework removal ({', '.join(fws_removed)}) simplifies the architecture.")

        if impact_parts:
            arch_impact = " ".join(impact_parts)
            parts.append(arch_impact)

        # --- Risk indicators ---
        risks = self.detect_risks(comparison, new_twin)

        # --- Maturity assessment ---
        maturity = self._assess_maturity(comparison, old_twin, new_twin)

        return {
            "what_changed": what,
            "likely_reason": likely_reason if why_parts else "",
            "architectural_impact": arch_impact if impact_parts else "No significant architectural impact.",
            "risk_indicators": risks,
            "explanation": " ".join(parts),
            "maturity_assessment": maturity,
        }

    # --- 2. Evolution Insights ---

    def generate_evolution_insights(self, all_comparisons, all_versions):
        """Generate per-version-transition insights across the full history.

        Returns list of insight dicts, one per version transition.
        """
        insights = []
        for comp in all_comparisons:
            explanation = self.reason_change(comp)
            insight = {
                "from_version": comp.get("from_version", 0),
                "to_version": comp.get("to_version", 0),
                "has_changes": comp.get("has_changes", False),
                "narrative": explanation.get("explanation", ""),
                "maturity_assessment": explanation.get("maturity_assessment", ""),
                "risks": explanation.get("risk_indicators", []),
                "risk_count": len(explanation.get("risk_indicators", [])),
            }
            insights.append(insight)

        # Overall arc assessment
        total_risks = sum(i["risk_count"] for i in insights)
        changes_count = sum(1 for i in insights if i["has_changes"])
        overall = self._assess_evolution_arc(all_comparisons, all_versions)

        return {
            "per_transition": insights,
            "overall": overall,
            "total_risks": total_risks,
            "transitions_with_changes": changes_count,
        }

    # --- 3. Risk Detection ---

    def detect_risks(self, comparison, new_twin=None):
        """Detect risk indicators from a comparison result.

        Returns list of risk dicts with type, severity, message.
        """
        risks = []

        # Dependency growth
        deps_added = comparison.get("changed_dependencies", {}).get("added", [])
        if deps_added:
            if len(deps_added) >= 5:
                risks.append({
                    "type": "dependency_growth",
                    "severity": "high",
                    "message": f"Large dependency increase: {len(deps_added)} new dependencies added.",
                })
            elif len(deps_added) >= 3:
                risks.append({
                    "type": "dependency_growth",
                    "severity": "medium",
                    "message": f"Moderate dependency growth: {len(deps_added)} new dependencies.",
                })

        # Missing documentation
        doc_added = comparison.get("documentation_changes", {}).get("added", [])
        if new_twin and not doc_added:
            new_doc_count = len(new_twin.get("documentation", {}).get("files", []))
            if new_doc_count == 0:
                risks.append({
                    "type": "missing_documentation",
                    "severity": "high",
                    "message": "No documentation files found.",
                })
            elif new_doc_count < 3:
                risks.append({
                    "type": "missing_documentation",
                    "severity": "medium",
                    "message": f"Low documentation coverage: only {new_doc_count} doc file(s).",
                })

        # Architecture drift
        old_arch = comparison.get("changed_architecture", {})
        if old_arch:
            risks.append({
                "type": "architecture_drift",
                "severity": "medium",
                "message": "Architecture documentation changed — review for structural drift.",
            })

        # Large structural changes
        new_files = comparison.get("new_files", [])
        removed_files = comparison.get("removed_files", [])
        total_file_changes = len(new_files) + len(removed_files)
        if total_file_changes >= 10:
            risks.append({
                "type": "large_structural_change",
                "severity": "high",
                "message": f"Large structural change: {total_file_changes} file(s) added or removed.",
            })
        elif total_file_changes >= 5:
            risks.append({
                "type": "large_structural_change",
                "severity": "low",
                "message": f"Notable structural change: {total_file_changes} file(s) changed.",
            })

        # Deprecated technologies
        if new_twin:
            all_fws = [f.lower() for f in new_twin.get("project", {}).get("frameworks", [])]
            all_deps = [d.lower() for d in new_twin.get("dependencies", [])]
            detected_deprecated = DEPRECATED_TECHS & (set(all_fws) | set(all_deps))
            for dt in detected_deprecated:
                risks.append({
                    "type": "deprecated_technology",
                    "severity": "high",
                    "message": f"Deprecated technology detected: {dt}.",
                })

        # Framework churn
        fws_removed = comparison.get("changed_frameworks", {}).get("removed", [])
        if fws_removed and len(fws_removed) >= 2:
            risks.append({
                "type": "framework_churn",
                "severity": "medium",
                "message": f"Multiple frameworks removed ({', '.join(fws_removed)}) — review for instability.",
            })

        # Classification instability
        if comparison.get("classification_changed"):
            risks.append({
                "type": "identity_drift",
                "severity": "low",
                "message": "Project domain classification changed — project identity may be shifting.",
            })

        return risks

    # --- Internal helpers ---

    def _assess_maturity(self, comparison, old_twin, new_twin):
        """Assess project maturity change based on comparison."""
        signals = []
        if not old_twin or not new_twin:
            return "Initial assessment — no prior baseline."

        old_dep_count = len(old_twin.get("dependencies", []))
        new_dep_count = len(new_twin.get("dependencies", []))
        old_doc_count = len(old_twin.get("documentation", {}).get("files", []))
        new_doc_count = len(new_twin.get("documentation", {}).get("files", []))
        old_fw_count = len(old_twin.get("project", {}).get("frameworks", []))
        new_fw_count = len(new_twin.get("project", {}).get("frameworks", []))

        if new_dep_count > old_dep_count:
            signals.append("dependency scope expanded")
        if new_doc_count > old_doc_count:
            signals.append("documentation improved")
        if new_fw_count > old_fw_count:
            signals.append("technology stack broadened")
        if new_fw_count < old_fw_count:
            signals.append("technology stack simplified")
        if comparison.get("classification_changed"):
            signals.append("domain classification evolved")

        if not signals:
            return "Project maturity stable — no measurable changes."
        return "Project maturity increased: " + "; ".join(signals) + "."

    def _assess_evolution_arc(self, all_comparisons, all_versions):
        """Assess overall evolution arc across all version transitions."""
        if len(all_comparisons) < 1:
            return "Insufficient history for arc assessment."

        dep_growth_count = 0
        doc_improvement_count = 0
        arch_changes = 0
        total_deps_added = 0

        for comp in all_comparisons:
            deps_added = comp.get("changed_dependencies", {}).get("added", [])
            if deps_added:
                dep_growth_count += 1
                total_deps_added += len(deps_added)
            docs_added = comp.get("documentation_changes", {}).get("added", [])
            if docs_added:
                doc_improvement_count += 1
            if comp.get("changed_architecture"):
                arch_changes += 1

        arc_parts = []
        if dep_growth_count > 0:
            arc_parts.append(f"dependency base grew by {total_deps_added} across {dep_growth_count} transition(s)")
        if doc_improvement_count > 0:
            arc_parts.append(f"documentation improved in {doc_improvement_count} transition(s)")
        if arch_changes > 0:
            arc_parts.append(f"architecture documentation changed in {arch_changes} transition(s)")

        change_freq = len(all_comparisons)
        if arc_parts:
            return f"Over {change_freq} version transition(s): " + "; ".join(arc_parts) + "."
        return f"Project remained stable across {change_freq} version transition(s)."
