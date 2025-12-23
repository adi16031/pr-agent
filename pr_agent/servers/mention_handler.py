"""
Handles @blackbox mentions in PR comments and dispatches appropriate workflows.

This module provides utilities to parse @blackbox mentions from comments and
extract the command/workflow to be triggered. It supports:
- @blackbox review (PR review workflow)
- @blackbox describe (PR description workflow)
- @blackbox improve (Code suggestions workflow)
- @blackbox scan (Vulnerability scan workflow)
- @blackbox ask "question" (Ask a question about the PR)
- And other supported commands
"""

import re
from typing import Optional, Tuple
from pr_agent.log import get_logger

# Pattern to match @blackbox mentions (case-insensitive)
# Matches: @blackbox, @Blackbox, @BLACKBOX followed by optional command
MENTION_PATTERN = re.compile(
    r'@blackbox\s+([a-z_\-]+)',
    re.IGNORECASE
)

# Supported workflows and their aliases
WORKFLOW_COMMANDS = {
    # Review workflows
    'review': {
        'aliases': ['review_pr', 'review_code'],
        'workflow': 'review',
        'description': 'Trigger a comprehensive PR review'
    },
    # Describe workflows
    'describe': {
        'aliases': ['describe_pr', 'description'],
        'workflow': 'describe',
        'description': 'Generate or update PR description'
    },
    # Code improvement suggestions
    'improve': {
        'aliases': ['improve_code', 'suggestions'],
        'workflow': 'improve',
        'description': 'Get code improvement suggestions'
    },
    # Vulnerability scanning
    'scan': {
        'aliases': ['vuln', 'vulnerability', 'security'],
        'workflow': 'scan',
        'description': 'Run vulnerability and security scan'
    },
    # Ask questions
    'ask': {
        'aliases': ['question', 'ask_question'],
        'workflow': 'ask',
        'description': 'Ask a question about the PR'
    },
    # Update changelog
    'changelog': {
        'aliases': ['update_changelog'],
        'workflow': 'update_changelog',
        'description': 'Update changelog based on PR contents'
    },
    # Generate labels
    'labels': {
        'aliases': ['generate_labels', 'label'],
        'workflow': 'generate_labels',
        'description': 'Generate appropriate labels for the PR'
    },
    # Add documentation
    'docs': {
        'aliases': ['add_docs', 'documentation'],
        'workflow': 'add_docs',
        'description': 'Generate documentation for the PR changes'
    },
    # Reflect (ask author questions)
    'reflect': {
        'aliases': [],
        'workflow': 'reflect',
        'description': 'Ask the PR author questions about the PR'
    },
    # Help docs
    'help_docs': {
        'aliases': ['help', 'search_docs'],
        'workflow': 'help_docs',
        'description': 'Search documentation for answers'
    },
}


def is_mention_present(comment_body: str) -> bool:
    """
    Check if a comment contains an @blackbox mention.

    Args:
        comment_body: The comment text to check

    Returns:
        bool: True if @blackbox mention is found, False otherwise
    """
    if not comment_body or not isinstance(comment_body, str):
        return False
    return bool(MENTION_PATTERN.search(comment_body))


def parse_mention(comment_body: str) -> Optional[Tuple[str, Optional[str]]]:
    """
    Parse @blackbox mention from comment and extract the command.

    Handles patterns like:
    - @blackbox review
    - @Blackbox Review (case-insensitive)
    - @blackbox review --some_config=value
    - @blackbox scan
    - @blackbox ask "What about this function?"

    Args:
        comment_body: The comment text to parse

    Returns:
        Tuple of (command, rest_of_comment) or None if no mention found
        - command: The normalized command (e.g., 'review', 'scan')
        - rest_of_comment: The rest of the comment after the command (for additional args/questions)
    """
    if not comment_body or not isinstance(comment_body, str):
        return None

    # Find the mention
    match = MENTION_PATTERN.search(comment_body)
    if not match:
        return None

    # Extract command and everything after it
    command = match.group(1).lower()

    # Get rest of comment after the matched text
    rest_start = match.end()
    rest_of_comment = comment_body[rest_start:].strip() if rest_start < len(comment_body) else ""

    # Normalize command to primary workflow command
    normalized_command = normalize_command(command)
    if normalized_command:
        return (normalized_command, rest_of_comment)

    return None


def normalize_command(command: str) -> Optional[str]:
    """
    Normalize a command string to its primary workflow command.

    Maps aliases to their primary command names.
    E.g., 'review_pr' -> 'review', 'vuln' -> 'scan'

    Args:
        command: The command string to normalize

    Returns:
        The normalized command name, or None if command is not supported
    """
    if not command:
        return None

    command = command.lower().strip()

    # Check if it's a primary command
    if command in WORKFLOW_COMMANDS:
        return command

    # Check if it's an alias
    for primary, config in WORKFLOW_COMMANDS.items():
        if command in config['aliases']:
            return primary

    return None


def get_all_supported_commands() -> list:
    """
    Get list of all supported primary commands.

    Returns:
        List of primary command names
    """
    return list(WORKFLOW_COMMANDS.keys())


def get_command_info(command: str) -> Optional[dict]:
    """
    Get information about a specific command.

    Args:
        command: The primary command name

    Returns:
        Dict with command info (aliases, workflow, description) or None
    """
    normalized = normalize_command(command)
    if normalized and normalized in WORKFLOW_COMMANDS:
        return WORKFLOW_COMMANDS[normalized]
    return None


def build_help_message() -> str:
    """
    Build a help message listing all supported @blackbox commands.

    Returns:
        Formatted help message
    """
    message = "# 🤖 @blackbox Commands\n\nSupported commands:\n\n"

    for cmd, config in WORKFLOW_COMMANDS.items():
        aliases_str = f" (aliases: {', '.join(config['aliases'])})" if config['aliases'] else ""
        message += f"- **@blackbox {cmd}** - {config['description']}{aliases_str}\n"

    message += "\n## Examples:\n"
    message += "- `@blackbox review` - Run a comprehensive code review\n"
    message += "- `@blackbox describe` - Update the PR description\n"
    message += "- `@blackbox scan` - Run security/vulnerability scan\n"
    message += "- `@blackbox improve` - Get code improvement suggestions\n"
    message += "- `@blackbox ask \"Why was this approach chosen?\"` - Ask a question\n"

    return message


def extract_question_from_comment(comment_body: str, command: str) -> Optional[str]:
    """
    Extract question content from an @blackbox ask command.

    Handles patterns like:
    - @blackbox ask "What is this function doing?"
    - @blackbox ask 'Is this secure?'
    - @blackbox ask How many functions changed?

    Args:
        comment_body: The full comment body
        command: Should be 'ask' for this to work

    Returns:
        The extracted question, or None if no question found
    """
    if command != 'ask':
        return None

    # Get everything after the command
    match = MENTION_PATTERN.search(comment_body)
    if not match:
        return None

    rest = comment_body[match.end():].strip()

    # Try to extract quoted question
    quoted_match = re.search(r'["\'](.*?)["\']', rest)
    if quoted_match:
        return quoted_match.group(1)

    # Return everything after the command as the question
    if rest:
        return rest

    return None


def format_command_for_cli(command: str, rest_of_comment: Optional[str] = None) -> str:
    """
    Format a parsed @blackbox command into a CLI command string.

    Args:
        command: The normalized command name
        rest_of_comment: Any additional content after the command

    Returns:
        Formatted command string for CLI execution
    """
    if not command:
        return ""

    # Start with the command
    cli_command = command

    # Add rest of comment if present
    if rest_of_comment and rest_of_comment.strip():
        cli_command += f" {rest_of_comment}"

    return cli_command


# Logging helper
def log_mention_parsed(comment_id: str, command: str, rest: Optional[str] = None):
    """Log parsed @blackbox mention for debugging."""
    rest_preview = (rest[:50] + "...") if rest and len(rest) > 50 else rest
    get_logger().info(
        f"Parsed @blackbox mention in comment {comment_id}: "
        f"command='{command}', rest='{rest_preview}'"
    )
