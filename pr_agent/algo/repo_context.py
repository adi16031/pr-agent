"""
Repository Context Module

This module provides utilities to extract and analyze repository-wide context
for enhanced PR reviews. It analyzes file relationships, architectural patterns,
and codebase conventions to provide contextual insights.
"""

import os
import traceback
from typing import Dict, List, Set, Optional, Tuple
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
        self._cache = {}

    def get_repository_context(self, modified_files: List[str]) -> Dict:
        """
        Extract comprehensive repository context based on modified files.

        Args:
            modified_files: List of file paths that are modified in the PR

        Returns:
            Dictionary containing repository context insights
        """
        try:
            if get_settings().config.get("repo_context_enabled", False) is False:
                self.logger.debug("Repository context analysis is disabled")
                return {}

            context = {
                "related_files": self._get_related_files(modified_files),
                "architectural_patterns": self._identify_architectural_patterns(modified_files),
                "language_specific_conventions": self._get_language_conventions(modified_files),
                "dependencies_impact": self._analyze_dependencies_impact(modified_files),
                "code_patterns": self._extract_code_patterns(modified_files),
                "similar_implementations": self._find_similar_implementations(modified_files),
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

    def _identify_architectural_patterns(self, modified_files: List[str]) -> Dict:
        """
        Identify architectural patterns and layers in the codebase.
        """
        try:
            patterns = {
                "layers": self._detect_layers(modified_files),
                "architecture_type": self._detect_architecture_type(modified_files),
                "module_organization": self._analyze_module_organization(modified_files),
            }
            return patterns
        except Exception as e:
            self.logger.debug(f"Error identifying architectural patterns: {e}")
            return {}

    def _detect_layers(self, modified_files: List[str]) -> List[str]:
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

        for file in modified_files:
            for layer, patterns in layer_indicators.items():
                if any(pattern in file for pattern in patterns):
                    layers.add(layer)

        return list(layers)

    def _detect_architecture_type(self, modified_files: List[str]) -> str:
        """
        Detect the architecture type (MVC, microservices, monolithic, etc.).
        """
        architecture = "unknown"

        # Check for microservices indicators
        if any("service" in f for f in modified_files) and any("api" in f for f in modified_files):
            architecture = "microservices"
        # Check for MVC indicators
        elif any(layer in modified_files for layer in ["models", "views", "controllers"]):
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

    def _analyze_module_organization(self, modified_files: List[str]) -> Dict:
        """
        Analyze how modules are organized in the project.
        """
        modules = defaultdict(list)
        for file in modified_files:
            parts = file.split("/")
            if len(parts) > 1:
                module = parts[0]
                modules[module].append(file)

        return dict(modules)

    def _get_language_conventions(self, modified_files: List[str]) -> Dict:
        """
        Extract language-specific conventions and patterns.
        """
        conventions = {
            "primary_language": self._detect_primary_language(modified_files),
            "naming_conventions": self._extract_naming_conventions(modified_files),
            "import_style": self._detect_import_style(modified_files),
        }
        return conventions

    def _detect_primary_language(self, modified_files: List[str]) -> str:
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

        for file in modified_files:
            ext = os.path.splitext(file)[1]
            if ext in language_map:
                ext_count[language_map[ext]] += 1

        if ext_count:
            return max(ext_count, key=ext_count.get)
        return "unknown"

    def _extract_naming_conventions(self, modified_files: List[str]) -> Dict:
        """
        Extract naming conventions used in the project.
        """
        conventions = {
            "file_naming": "unknown",
            "directory_naming": "unknown",
        }

        # Analyze file naming patterns
        snake_case_files = sum(1 for f in modified_files if "_" in os.path.basename(f))
        kebab_case_files = sum(1 for f in modified_files if "-" in os.path.basename(f))
        camel_case_files = sum(1 for f in modified_files if os.path.basename(f)[0].islower() and any(c.isupper() for c in os.path.basename(f)))

        if snake_case_files > kebab_case_files and snake_case_files > camel_case_files:
            conventions["file_naming"] = "snake_case"
        elif kebab_case_files > snake_case_files:
            conventions["file_naming"] = "kebab_case"
        elif camel_case_files > 0:
            conventions["file_naming"] = "camelCase"

        return conventions

    def _detect_import_style(self, modified_files: List[str]) -> str:
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

    def _extract_code_patterns(self, modified_files: List[str]) -> Dict:
        """
        Extract common code patterns and practices used in the repository.
        """
        patterns = {
            "uses_decorators": False,
            "uses_interfaces": False,
            "uses_inheritance": False,
            "testing_framework": self._detect_testing_framework(modified_files),
            "logging_approach": "standard",
        }
        return patterns

    def _detect_testing_framework(self, modified_files: List[str]) -> str:
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
        for file in modified_files:
            if "test" in file.lower():
                return "detected"

        return "unknown"

    def _find_similar_implementations(self, modified_files: List[str]) -> List[str]:
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
            # This is a simplified check - in production, we'd use git provider methods
            return False  # Placeholder
        except Exception:
            return False


class RepositoryContextProvider:
    """
    Provides formatted repository context for use in PR review prompts.
    """

    def __init__(self, git_provider: GitProvider):
        self.analyzer = RepoContextAnalyzer(git_provider)
        self.logger = get_logger()

    def get_context_str(self, modified_files: List[str]) -> str:
        """
        Get a formatted string representation of repository context.
        """
        try:
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


def get_repo_context(git_provider: GitProvider, modified_files: List[str]) -> str:
    """
    Convenience function to get formatted repository context.
    """
    try:
        provider = RepositoryContextProvider(git_provider)
        return provider.get_context_str(modified_files)
    except Exception as e:
        get_logger().warning(f"Failed to get repository context: {e}")
        return ""
