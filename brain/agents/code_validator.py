"""
Code Validator for CodeExecution Tool
Validates Python code before sandbox execution to catch common issues.
"""

import ast
import re
from typing import Tuple, Optional


class CodeValidator:
    """
    Validates Python code before execution to improve success rate.

    Checks for:
    - Syntax errors
    - Missing print() statements
    - Dangerous imports
    - Common patterns that won't produce output
    """

    # Dangerous modules blocked in sandbox
    BLOCKED_MODULES = {
        'os', 'subprocess', 'sys', 'socket', 'urllib',
        'requests', 'httpx', 'shutil', 'pathlib',
        '__import__', 'eval', 'exec', 'compile'
    }

    # Modules that are safe and commonly used
    SAFE_MODULES = {
        'math', 'random', 'datetime', 'json', 're',
        'itertools', 'functools', 'collections', 'string'
    }

    def validate(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Validate code before execution.

        Args:
            code: Python code to validate

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if code should execute, False if issues found
            - error_message: None if valid, descriptive error if invalid
        """
        # Empty check
        if not code or not code.strip():
            return False, "Code is empty"

        code = code.strip()

        # Length check
        if len(code) > 5000:
            return False, f"Code too long ({len(code)} chars). Maximum 5000 characters."

        # Syntax check
        syntax_valid, syntax_error = self._check_syntax(code)
        if not syntax_valid:
            return False, f"Syntax error: {syntax_error}"

        # Dangerous imports check
        dangerous_found, dangerous_msg = self._check_dangerous_imports(code)
        if dangerous_found:
            return False, dangerous_msg

        # Output check (warn if no print statements)
        has_output, output_msg = self._check_has_output(code)
        if not has_output:
            # This is a warning, not a blocker - let code execute but provide helpful message
            return True, output_msg

        # All checks passed
        return True, None

    def _check_syntax(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Check if code has valid Python syntax.

        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            ast.parse(code)
            return True, None
        except SyntaxError as e:
            # Format helpful error message
            msg = f"Line {e.lineno}: {e.msg}"
            if e.text:
                msg += f"\n  Code: {e.text.strip()}"
            return False, msg
        except Exception as e:
            return False, str(e)

    def _check_dangerous_imports(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Check for dangerous imports that are blocked in sandbox.

        Returns:
            Tuple of (found_dangerous, error_message)
        """
        # Parse imports from code
        try:
            tree = ast.parse(code)
        except:
            # If can't parse, let syntax checker handle it
            return False, None

        dangerous_imports = []

        for node in ast.walk(tree):
            # Check "import X" statements
            if isinstance(node, ast.Import):
                for name in node.names:
                    module = name.name.split('.')[0]
                    if module in self.BLOCKED_MODULES:
                        dangerous_imports.append(module)

            # Check "from X import Y" statements
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    module = node.module.split('.')[0]
                    if module in self.BLOCKED_MODULES:
                        dangerous_imports.append(module)

        if dangerous_imports:
            modules_str = ', '.join(dangerous_imports)
            return True, (
                f"Blocked imports detected: {modules_str}\n"
                f"These modules are disabled in the sandbox for security.\n"
                f"Safe modules: {', '.join(sorted(self.SAFE_MODULES))}"
            )

        return False, None

    def _check_has_output(self, code: str) -> Tuple[bool, Optional[str]]:
        """
        Check if code is likely to produce output.

        Returns:
            Tuple of (has_output, warning_message)
            - has_output: True if code will likely produce output
            - warning_message: Helpful hint if no output expected
        """
        # Parse code
        try:
            tree = ast.parse(code)
        except:
            # If can't parse, let syntax checker handle it
            return True, None

        # Check for print() calls
        has_print = self._has_print_call(tree)

        if has_print:
            return True, None

        # Check if code only defines functions/classes without calling them
        defines_function = False
        defines_class = False
        has_executable_statements = False

        for node in tree.body:
            if isinstance(node, ast.FunctionDef):
                defines_function = True
            elif isinstance(node, ast.ClassDef):
                defines_class = True
            elif isinstance(node, (ast.Assign, ast.AugAssign, ast.Expr)):
                # These are executable statements
                has_executable_statements = True

        # Generate helpful warning based on what we found
        if defines_function and not has_executable_statements:
            return False, (
                "WARNING: Your code defines a function but doesn't call it or print the result.\n"
                "Add a print statement, like: print(my_function(arguments))\n"
                "Code will execute, but you won't see any output."
            )

        if defines_class and not has_executable_statements:
            return False, (
                "WARNING: Your code defines a class but doesn't use it or print anything.\n"
                "Create an instance and print the result, like: obj = MyClass(); print(obj.method())\n"
                "Code will execute, but you won't see any output."
            )

        if has_executable_statements:
            # Code has statements but no print
            return False, (
                "WARNING: Your code runs calculations but doesn't print the result.\n"
                "Add print() to see the output, like: print(result)\n"
                "Code will execute, but you won't see any output."
            )

        # Empty module or imports only
        return False, (
            "WARNING: Your code doesn't appear to do anything or produce output.\n"
            "Add print() statements to see results."
        )

    def _has_print_call(self, tree: ast.AST) -> bool:
        """
        Check if AST contains any print() calls.

        Args:
            tree: Parsed AST tree

        Returns:
            True if print() is called anywhere in the code
        """
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                # Check if this is a print() call
                if isinstance(node.func, ast.Name) and node.func.id == 'print':
                    return True
        return False


# Global validator instance
_validator = CodeValidator()


def validate_code(code: str) -> Tuple[bool, Optional[str]]:
    """
    Validate Python code before execution.

    Args:
        code: Python code to validate

    Returns:
        Tuple of (is_valid, message)
        - is_valid: True if code should execute, False if critical issues found
        - message: None if valid, error/warning message otherwise

    Examples:
        >>> validate_code("print(2 + 2)")
        (True, None)

        >>> validate_code("result = 2 + 2")
        (True, "WARNING: Your code runs calculations but doesn't print the result...")

        >>> validate_code("import os")
        (False, "Blocked imports detected: os...")

        >>> validate_code("print(2 +)")
        (False, "Syntax error: invalid syntax...")
    """
    return _validator.validate(code)
