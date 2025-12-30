"""
Repository Context Module

This module provides utilities to extract and analyze repository-wide context
for enhanced PR reviews. It analyzes file relationships, architectural patterns,
and codebase conventions to provide contextual insights.
"""

import os
import re
import traceback
from tempfile import TemporaryDirectory
from typing import Dict, List, Set, Optional
from collections import defaultdict

from pr_agent.log import get_logger
from pr_agent.config_loader import get_settings
from pr_agent.git_providers.git_provider import GitProvider


class RepoContextAnalyzer:
    """
    Analyzes repository context to provide architectural and code pattern insights
    for enhanced PR reviews.
    """

    def __init__(self, git_provider: GitProvider):
        self.git_provider = git_provider
        self.logger = get_logger()
        self._repo_files_set: Optional[Set[str]] = None
        self._repo_root: Optional[str] = None

    def get_repository_context(self, modified_files: List[str], repo_files: Optional[List[str]] = None,
                               repo_root: Optional[str] = None) -> Dict:
        """
        Extract comprehensive repository context based on repository-wide files.

        Args:
            modified_files: List of file paths that are modified in the PR
            repo_files: Optional list of file paths representing the entire repo
            repo_root: Optional filesystem path to the repo root for file content analysis

        Returns:
            Dictionary containing repository context insights
        """
        try:
            if get_settings().config.get("repo_context_enabled", False) is False:
                self.logger.debug("Repository context analysis is disabled")
                return {}

            analysis_files = repo_files or modified_files
            self._set_repo_files(repo_files or [])
            self._set_repo_root(repo_root)

            context = {
                "related_files": self._get_related_files(modified_files),
                "architectural_patterns": self._identify_architectural_patterns(analysis_files),
                "language_specific_conventions": self._get_language_conventions(analysis_files),
                "dependencies_impact": self._analyze_dependencies_impact(modified_files),
                "code_patterns": self._extract_code_patterns(analysis_files),
                "similar_implementations": self._find_similar_implementations(analysis_files),
            }

            self.logger.debug(f"Repository context analysis completed", artifact=context)
            return context

        except Exception as e:
            self.logger.warning(f"Failed to analyze repository context: {e}",
                              artifact={"traceback": traceback.format_exc()})
            return {}

    def _get_related_files(self, modified_files: List[str]) -> Dict[str, List[str]]:
        """
        Identify related files that might be affected by the changes.

        Returns:
            Dictionary mapping file categories to related files
        """
        try:
            related_files = {
                "test_files": [],
                "config_files": [],
                "documentation_files": [],
                "imported_by": [],
                "imports_from": [],
            }

            for file in modified_files:
                # Find corresponding test files
                test_file = self._find_test_file(file)
                if test_file:
                    related_files["test_files"].append(test_file)

            # Identify config files that might be affected
            related_files["config_files"] = self._find_affected_config_files(modified_files)

            # Find related documentation
            related_files["documentation_files"] = self._find_related_docs(modified_files)

            self._populate_import_relationships(modified_files, related_files)
            return related_files
        except Exception as e:
            self.logger.debug(f"Error analyzing related files: {e}")
            return {}

    def _find_test_file(self, source_file: str) -> Optional[str]:
        """
        Find the corresponding test file for a source file.
        """
        try:
            # Common test file patterns
            patterns = [
                (source_file.replace(".py", "_test.py"), ".py"),
                (source_file.replace(".py", ".test.py"), ".py"),
                (source_file.replace(".js", ".test.js"), ".js"),
                (source_file.replace(".ts", ".test.ts"), ".ts"),
                (source_file.replace(".ts", ".spec.ts"), ".ts"),
            ]

            for test_path, ext in patterns:
                if test_path != source_file and self._file_exists_in_repo(test_path):
                    return test_path

            # Check in test directory
            parts = source_file.split("/")
            for i, part in enumerate(parts):
                if part in ["src", "lib", "main"]:
                    test_path = "/".join(parts[:i] + ["test", "__tests__", "tests"] + parts[i:])
                    if self._file_exists_in_repo(test_path):
                        return test_path

            return None
        except Exception as e:
            self.logger.debug(f"Error finding test file for {source_file}: {e}")
            return None

    def _find_affected_config_files(self, modified_files: List[str]) -> List[str]:
        """
        Identify configuration files that might be affected by the changes.
        """
        config_patterns = [
            "setup.py", "pyproject.toml", "requirements.txt",
            "package.json", "tsconfig.json", "webpack.config.js",
            ".env", "docker-compose.yml", "Dockerfile",
            "Makefile", "CMakeLists.txt",
        ]

        affected_configs = []
        for config in config_patterns:
            if self._file_exists_in_repo(config):
                affected_configs.append(config)

        return affected_configs

    def _find_related_docs(self, modified_files: List[str]) -> List[str]:
        """
        Find documentation files related to modified files.
        """
        docs = []
        doc_extensions = [".md", ".rst", ".txt"]

        for file in modified_files:
            base_name = os.path.splitext(file)[0]
            for ext in doc_extensions:
                doc_path = base_name + ext
                if self._file_exists_in_repo(doc_path):
                    docs.append(doc_path)

        # Check for README and CHANGELOG
        for doc in ["README.md", "CHANGELOG.md", "docs/index.md"]:
            if self._file_exists_in_repo(doc):
                docs.append(doc)

        return docs

    def _identify_architectural_patterns(self, repo_files: List[str]) -> Dict:
        """
        Identify architectural patterns and layers in the codebase.
        """
        try:
            patterns = {
                "layers": self._detect_layers(repo_files),
                "architecture_type": self._detect_architecture_type(repo_files),
                "module_organization": self._analyze_module_organization(repo_files),
            }
            return patterns
        except Exception as e:
            self.logger.debug(f"Error identifying architectural patterns: {e}")
            return {}

    def _detect_layers(self, repo_files: List[str]) -> List[str]:
        """
        Detect if the project follows a layered architecture (e.g., models, views, controllers).
        """
        layers = set()
        layer_indicators = {
            "models": ["models/", "model.py", "entities/"],
            "views": ["views/", "view.py", "ui/", "templates/"],
            "controllers": ["controllers/", "controller.py", "handlers/", "handlers.py"],
            "services": ["services/", "service.py", "business/"],
            "repositories": ["repositories/", "repository.py", "repos/", "data/"],
            "middleware": ["middleware/", "middlewares/"],
            "utils": ["utils/", "util.py", "helpers/"],
        }

        for file in repo_files:
            for layer, patterns in layer_indicators.items():
                if any(pattern in file for pattern in patterns):
                    layers.add(layer)

        return list(layers)

    def _detect_architecture_type(self, repo_files: List[str]) -> str:
        """
        Detect the architecture type (MVC, microservices, monolithic, etc.).
        """
        architecture = "unknown"

        # Check for microservices indicators
        if any("service" in f for f in repo_files) and any("api" in f for f in repo_files):
            architecture = "microservices"
        # Check for MVC indicators
        elif any(layer in repo_files for layer in ["models", "views", "controllers"]):
            architecture = "mvc"
        # Check for module-based architecture
        elif self._detect_module_based():
            architecture = "modular"
        else:
            architecture = "monolithic"

        return architecture

    def _detect_module_based(self) -> bool:
        """Check if project uses module-based architecture."""
        try:
            root_files = os.listdir(self.git_provider.repo_dir or ".")
            # Look for __init__.py files indicating Python packages
            init_count = len([f for f in root_files if f == "__init__.py"])
            return init_count > 0
        except Exception:
            return False

    def _analyze_module_organization(self, repo_files: List[str]) -> Dict:
        """
        Analyze how modules are organized in the project.
        """
        modules = defaultdict(list)
        for file in repo_files:
            parts = file.split("/")
            if len(parts) > 1:
                module = parts[0]
                modules[module].append(file)

        return dict(modules)

    def _get_language_conventions(self, repo_files: List[str]) -> Dict:
        """
        Extract language-specific conventions and patterns.
        """
        conventions = {
            "primary_language": self._detect_primary_language(repo_files),
            "naming_conventions": self._extract_naming_conventions(repo_files),
            "import_style": self._detect_import_style(repo_files),
        }
        return conventions

    def _detect_primary_language(self, repo_files: List[str]) -> str:
        """
        Detect the primary programming language used in modified files.
        """
        ext_count = defaultdict(int)
        language_map = {
            ".py": "python",
            ".js": "javascript",
            ".ts": "typescript",
            ".java": "java",
            ".go": "go",
            ".rs": "rust",
            ".cpp": "cpp",
            ".cs": "csharp",
        }

        for file in repo_files:
            ext = os.path.splitext(file)[1]
            if ext in language_map:
                ext_count[language_map[ext]] += 1

        if ext_count:
            return max(ext_count, key=ext_count.get)
        return "unknown"

    def _extract_naming_conventions(self, repo_files: List[str]) -> Dict:
        """
        Extract naming conventions used in the project.
        """
        conventions = {
            "file_naming": "unknown",
            "directory_naming": "unknown",
        }

        # Analyze file naming patterns
        snake_case_files = sum(1 for f in repo_files if "_" in os.path.basename(f))
        kebab_case_files = sum(1 for f in repo_files if "-" in os.path.basename(f))
        camel_case_files = sum(1 for f in repo_files if os.path.basename(f)[0].islower() and any(c.isupper() for c in os.path.basename(f)))

        if snake_case_files > kebab_case_files and snake_case_files > camel_case_files:
            conventions["file_naming"] = "snake_case"
        elif kebab_case_files > snake_case_files:
            conventions["file_naming"] = "kebab_case"
        elif camel_case_files > 0:
            conventions["file_naming"] = "camelCase"

        return conventions

    def _detect_import_style(self, repo_files: List[str]) -> str:
        """
        Detect the import style used in the project (absolute vs relative imports).
        """
        return "mixed"  # Default to mixed as we need file content analysis

    def _analyze_dependencies_impact(self, modified_files: List[str]) -> Dict:
        """
        Analyze how changes might impact project dependencies.
        """
        impact = {
            "modified_dependencies": [],
            "affected_modules": [],
            "breaking_changes_risk": "low",
        }

        # Check if dependency files are modified
        dependency_files = ["requirements.txt", "package.json", "pyproject.toml", "Gemfile", "go.mod"]
        for file in modified_files:
            if os.path.basename(file) in dependency_files:
                impact["modified_dependencies"].append(file)
                impact["breaking_changes_risk"] = "high"

        return impact

    def _extract_code_patterns(self, repo_files: List[str]) -> Dict:
        """
        Extract common code patterns and practices used in the repository.
        """
        patterns = {
            "uses_decorators": False,
            "uses_interfaces": False,
            "uses_inheritance": False,
            "testing_framework": self._detect_testing_framework(repo_files),
            "logging_approach": "standard",
        }
        return patterns

    def _detect_testing_framework(self, repo_files: List[str]) -> str:
        """
        Detect the testing framework used in the project.
        """
        testing_frameworks = {
            "pytest": ".py",
            "unittest": ".py",
            "jest": ".js",
            "mocha": ".js",
            "jasmine": ".ts",
            "junit": ".java",
            "golang testing": ".go",
        }

        # Look for test dependencies
        for file in repo_files:
            if "test" in file.lower():
                return "detected"

        return "unknown"

    def _find_similar_implementations(self, repo_files: List[str]) -> List[str]:
        """
        Find similar implementations in the codebase that could be referenced or refactored.
        """
        similar = []
        # This would require more sophisticated analysis
        # For now, return empty list as a placeholder
        return similar

    def _file_exists_in_repo(self, file_path: str) -> bool:
        """
        Check if a file exists in the repository.
        """
        try:
            if self._repo_files_set is not None:
                return file_path in self._repo_files_set
            return False
        except Exception:
            return False

    def _set_repo_files(self, repo_files: List[str]) -> None:
        if repo_files:
            self._repo_files_set = set(repo_files)
        else:
            self._repo_files_set = None

    def _set_repo_root(self, repo_root: Optional[str]) -> None:
        self._repo_root = repo_root

    def _populate_import_relationships(self, modified_files: List[str], related_files: Dict[str, List[str]]) -> None:
        if not self._repo_root or not self._repo_files_set:
            return

        imports_from = set()
        imported_by = set()
        repo_files = list(self._repo_files_set)

        imports_from_map = {}
        imported_by_map = {}
        for repo_file in repo_files:
            if not self._is_import_scannable(repo_file):
                continue
            contents = self._read_repo_file(repo_file)
            if not contents:
                continue
            resolved_imports = self._resolve_imports(repo_file, contents)
            if not resolved_imports:
                continue
            imports_from_map[repo_file] = resolved_imports
            for imported in resolved_imports:
                imported_by_map.setdefault(imported, set()).add(repo_file)

        for file in modified_files:
            imports_from.update(imports_from_map.get(file, set()))
            imported_by.update(imported_by_map.get(file, set()))

        related_files["imports_from"] = sorted(imports_from)
        related_files["imported_by"] = sorted(imported_by)

    def _read_repo_file(self, rel_path: str) -> str:
        if not self._repo_root:
            return ""
        abs_path = os.path.join(self._repo_root, rel_path)
        try:
            with open(abs_path, "r", encoding="utf-8", errors="ignore") as handle:
                return handle.read()
        except Exception:
            return ""

    def _is_import_scannable(self, file_path: str) -> bool:
        return os.path.splitext(file_path)[1] in {".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}

    def _resolve_imports(self, file_path: str, contents: str) -> Set[str]:
        ext = os.path.splitext(file_path)[1]
        if ext == ".py":
            return self._resolve_python_imports(file_path, contents)
        return self._resolve_js_imports(file_path, contents)

    def _resolve_python_imports(self, file_path: str, contents: str) -> Set[str]:
        results = set()
        for match in re.finditer(r"^\s*import\s+([a-zA-Z0-9_.,\s]+)", contents, re.MULTILINE):
            modules_raw = match.group(1)
            for module in modules_raw.split(","):
                module_name = module.strip().split(" as ")[0].strip()
                results.update(self._resolve_python_module(file_path, module_name))

        for match in re.finditer(r"^\s*from\s+([a-zA-Z0-9_\.]+)\s+import\s+", contents, re.MULTILINE):
            module_name = match.group(1).strip()
            results.update(self._resolve_python_module(file_path, module_name))
        return results

    def _resolve_python_module(self, file_path: str, module_name: str) -> Set[str]:
        if not module_name:
            return set()
        base_dir = os.path.dirname(file_path)
        if module_name.startswith("."):
            leading = len(module_name) - len(module_name.lstrip("."))
            rel_module = module_name.lstrip(".")
            target_dir = base_dir
            for _ in range(max(leading - 1, 0)):
                target_dir = os.path.dirname(target_dir)
            if rel_module:
                target_dir = os.path.normpath(os.path.join(target_dir, rel_module.replace(".", "/")))
            else:
                target_dir = os.path.normpath(target_dir)
        else:
            target_dir = module_name.replace(".", "/")

        candidates = [
            f"{target_dir}.py",
            os.path.join(target_dir, "__init__.py"),
        ]
        return self._filter_existing_candidates(candidates)

    def _resolve_js_imports(self, file_path: str, contents: str) -> Set[str]:
        results = set()
        patterns = [
            r"^\s*import\s+.*?\s+from\s+['\"]([^'\"]+)['\"]",
            r"^\s*import\s+['\"]([^'\"]+)['\"]",
            r"require\(\s*['\"]([^'\"]+)['\"]\s*\)",
        ]
        for pattern in patterns:
            for match in re.finditer(pattern, contents, re.MULTILINE):
                module_name = match.group(1).strip()
                results.update(self._resolve_js_module(file_path, module_name))
        return results

    def _resolve_js_module(self, file_path: str, module_name: str) -> Set[str]:
        if not module_name.startswith("."):
            return set()
        base_dir = os.path.dirname(file_path)
        rel_path = os.path.normpath(os.path.join(base_dir, module_name))
        rel_path = rel_path.replace(os.sep, "/")

        candidates = []
        if os.path.splitext(rel_path)[1]:
            candidates.append(rel_path)
        else:
            for ext in [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"]:
                candidates.append(f"{rel_path}{ext}")
            for ext in [".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"]:
                candidates.append(f"{rel_path}/index{ext}")
        return self._filter_existing_candidates(candidates)

    def _filter_existing_candidates(self, candidates: List[str]) -> Set[str]:
        if not self._repo_files_set:
            return set()
        normalized = {c.replace(os.sep, "/") for c in candidates}
        return {c for c in normalized if c in self._repo_files_set}

    def _list_repo_files(self, repo_root: str) -> List[str]:
        repo_files = []
        max_files = int(get_settings().config.get("repo_context_max_files", 50))

        for root, dirs, files in os.walk(repo_root):
            dirs[:] = [d for d in dirs if d not in {".git", ".hg", ".svn"}]
            for file in files:
                rel_path = os.path.relpath(os.path.join(root, file), repo_root)
                rel_path = rel_path.replace(os.sep, "/")
                repo_files.append(rel_path)
                if max_files > 0 and len(repo_files) >= max_files:
                    return repo_files
        return repo_files

    def get_repo_root_from_provider(self, pr_url: Optional[str]) -> Optional[str]:
        try:
            repo_path = getattr(self.git_provider, "repo_path", None)
            if repo_path:
                return str(repo_path)
            repo_url = self.git_provider.get_git_repo_url(pr_url) if pr_url else ""
            if repo_url:
                return repo_url
            return None
        except Exception as e:
            self.logger.debug(f"Error fetching repository root: {e}")
            return None


class RepositoryContextProvider:
    """
    Provides formatted repository context for use in PR review prompts.
    """

    def __init__(self, git_provider: GitProvider):
        self.analyzer = RepoContextAnalyzer(git_provider)
        self.logger = get_logger()

    def get_context_str(self, modified_files: List[str], pr_url: Optional[str] = None) -> str:
        """
        Get a formatted string representation of repository context.
        """
        try:
            if get_settings().config.get("repo_context_enabled", False) is False:
                return ""
            repo_root = self.analyzer.get_repo_root_from_provider(pr_url)
            repo_files = []
            if repo_root and os.path.isdir(repo_root):
                repo_files = self.analyzer._list_repo_files(repo_root)
                if repo_files:
                    self.logger.debug("Using repository-wide files for context analysis",
                                      artifact={"num_files": len(repo_files)})
                context = self.analyzer.get_repository_context(
                    modified_files,
                    repo_files=repo_files or None,
                    repo_root=repo_root,
                )
            elif repo_root and isinstance(repo_root, str):
                with TemporaryDirectory() as tmp_dir:
                    returned_repo = self.analyzer.git_provider.clone(repo_root, tmp_dir, remove_dest_folder=False)
                    if not returned_repo:
                        context = self.analyzer.get_repository_context(modified_files)
                    else:
                        repo_files = self.analyzer._list_repo_files(returned_repo.path)
                        if repo_files:
                            self.logger.debug("Using repository-wide files for context analysis",
                                              artifact={"num_files": len(repo_files)})
                        context = self.analyzer.get_repository_context(
                            modified_files,
                            repo_files=repo_files or None,
                            repo_root=returned_repo.path,
                        )
            else:
                context = self.analyzer.get_repository_context(modified_files)

            if not context:
                return ""

            context_str = self._format_context(context)
            return context_str

        except Exception as e:
            self.logger.warning(f"Error generating context string: {e}")
            return ""

    def _format_context(self, context: Dict) -> str:
        """
        Format repository context into a readable string for the prompt.
        """
        parts = []

        parts.append("# Repository Context\n")

        # Related Files
        if context.get("related_files"):
            parts.append("## Related Files")
            related = context["related_files"]
            if related.get("test_files"):
                parts.append(f"- Test files: {', '.join(related['test_files'])}")
            if related.get("config_files"):
                parts.append(f"- Config files: {', '.join(related['config_files'])}")
            if related.get("documentation_files"):
                parts.append(f"- Documentation: {', '.join(related['documentation_files'])}")
            parts.append("")

        # Architectural Patterns
        if context.get("architectural_patterns"):
            patterns = context["architectural_patterns"]
            parts.append("## Architecture")
            if patterns.get("architecture_type"):
                parts.append(f"- Type: {patterns['architecture_type']}")
            if patterns.get("layers"):
                parts.append(f"- Layers: {', '.join(patterns['layers'])}")
            parts.append("")

        # Language Conventions
        if context.get("language_specific_conventions"):
            conventions = context["language_specific_conventions"]
            parts.append("## Code Conventions")
            if conventions.get("primary_language"):
                parts.append(f"- Language: {conventions['primary_language']}")
            if conventions.get("naming_conventions", {}).get("file_naming"):
                parts.append(f"- File naming: {conventions['naming_conventions']['file_naming']}")
            parts.append("")

        # Dependencies Impact
        if context.get("dependencies_impact"):
            impact = context["dependencies_impact"]
            if impact.get("modified_dependencies"):
                parts.append("## Dependencies Modified")
                parts.append(f"- {', '.join(impact['modified_dependencies'])}")
                parts.append(f"- Breaking changes risk: {impact.get('breaking_changes_risk', 'low')}")
                parts.append("")

        # Code Patterns
        if context.get("code_patterns"):
            patterns = context["code_patterns"]
            parts.append("## Code Patterns")
            if patterns.get("testing_framework"):
                parts.append(f"- Testing: {patterns['testing_framework']}")
            parts.append("")

        return "\n".join(parts)


def get_repo_context(git_provider: GitProvider, modified_files: List[str], pr_url: Optional[str] = None) -> str:
    """
    Convenience function to get formatted repository context.
    """
    try:
        provider = RepositoryContextProvider(git_provider)
        return provider.get_context_str(modified_files, pr_url=pr_url)
    except Exception as e:
        get_logger().warning(f"Failed to get repository context: {e}")
        return ""
