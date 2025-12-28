"""
Basic Tools for ReAct Agents (Chunk 3.2)
Simple tools for demonstration and testing.
"""

import math
import re
import operator
from typing import Any


async def calculator(expression: str) -> str:
    """
    Calculator tool - evaluates simple mathematical expressions safely.

    Args:
        expression: Math expression to evaluate (e.g., "2 + 2", "10 * 5")

    Returns:
        Result of the calculation

    Note: Uses safe operator lookup instead of eval()
    """
    try:
        # Clean the expression
        expression = expression.strip()

        # Strip common LLM-added quotes (similar to JSON tool optimization)
        if expression.startswith("'") and expression.endswith("'"):
            expression = expression[1:-1].strip()
        if expression.startswith('"') and expression.endswith('"'):
            expression = expression[1:-1].strip()

        # Define safe operators
        ops = {
            '+': operator.add,
            '-': operator.sub,
            '*': operator.mul,
            '/': operator.truediv,
            '//': operator.floordiv,
            '%': operator.mod,
            '**': operator.pow,
        }

        # Try multi-operand addition/subtraction (e.g., "150 + 200 + 175")
        # Only support + and - for multi-operand (safe and unambiguous)
        if '+' in expression or ('-' in expression and expression.count('-') > 1):
            # Check if this looks like a simple addition/subtraction chain
            # Pattern: numbers separated by + or - operators
            multi_pattern = r'^[\d\s+\-\.]+$'
            if re.match(multi_pattern, expression):
                # Split by operators while keeping track of operations
                # Replace - with +- to handle subtraction
                normalized = expression.replace(' ', '').replace('-', '+-')
                parts = [p for p in normalized.split('+') if p]

                try:
                    result = sum(float(p) for p in parts)
                    return f"Result: {result}"
                except ValueError:
                    pass  # Fall through to other patterns

        # Simple two-operand calculator
        # Parse: "number operator number"
        pattern = r'^\s*(-?\d+\.?\d*)\s*([+\-*/%]{1,2}|\*\*)\s*(-?\d+\.?\d*)\s*$'
        match = re.match(pattern, expression)

        if match:
            num1 = float(match.group(1))
            op = match.group(2)
            num2 = float(match.group(3))

            if op in ops:
                result = ops[op](num1, num2)
                return f"Result: {result}"
            else:
                return f"Error: Unsupported operator '{op}'"

        # Check for single number (just return it)
        if re.match(r'^\s*-?\d+\.?\d*\s*$', expression):
            return f"Result: {float(expression)}"

        # Check for math functions
        if expression.startswith('sqrt(') and expression.endswith(')'):
            num = float(expression[5:-1])
            return f"Result: {math.sqrt(num)}"

        if expression.startswith('abs(') and expression.endswith(')'):
            num = float(expression[4:-1])
            return f"Result: {abs(num)}"

        return "Error: Expression too complex. Supported: 'num op num', 'num + num + num' (addition/subtraction only), 'sqrt(num)', 'abs(num)'"

    except ValueError as e:
        return f"Error: Invalid number format"
    except ZeroDivisionError:
        return "Error: Division by zero"
    except Exception as e:
        return f"Error in calculation: {str(e)}"


async def string_length(text: str) -> str:
    """
    Get the length of a string.

    Args:
        text: Text to measure

    Returns:
        Length of the text
    """
    return f"The text has {len(text)} characters"


async def word_count(text: str) -> str:
    """
    Count words in text.

    Args:
        text: Text to analyze

    Returns:
        Number of words
    """
    words = text.split()
    return f"The text has {len(words)} words"


async def reverse_string(text: str) -> str:
    """
    Reverse a string.

    Args:
        text: Text to reverse

    Returns:
        Reversed text
    """
    return f"Reversed: {text[::-1]}"


async def to_uppercase(text: str) -> str:
    """
    Convert text to uppercase.

    Args:
        text: Text to convert

    Returns:
        Uppercase text
    """
    return f"Uppercase: {text.upper()}"


async def extract_numbers(text: str) -> str:
    """
    Extract all numbers from text.

    Args:
        text: Text to search

    Returns:
        List of numbers found
    """
    numbers = re.findall(r'-?\d+\.?\d*', text)
    if numbers:
        return f"Found numbers: {', '.join(numbers)}"
    else:
        return "No numbers found in the text"


# Tool registry for basic tools
BASIC_TOOLS = {
    "Calculator": (
        "Perform mathematical calculations safely. "
        "Supports: Two-operand (e.g., '15 * 23'), multi-operand addition/subtraction (e.g., '150 + 200 + 175'), "
        "and functions sqrt(num) and abs(num). "
        "Operations: +, -, *, /, //, %, **. "
        "Input: Just the expression (no extra quotes needed). "
        "Examples: '50 * 8', '100 + 200 + 50', 'sqrt(144)', '67 - 23'",
        calculator
    ),
    "StringLength": (
        "Count the number of characters in a text string. "
        "Use this to get the length of any text. "
        "Input format: the text string to measure",
        string_length
    ),
    "WordCount": (
        "Count the number of words in a text string. "
        "Use this to analyze text length or check word limits. "
        "Input format: the text string to count words in",
        word_count
    ),
    "ReverseString": (
        "Reverse the characters in a text string. "
        "Use this for string manipulation or checking palindromes. "
        "Input format: the text string to reverse",
        reverse_string
    ),
    "ToUppercase": (
        "Convert all characters in a text string to uppercase. "
        "Use this for text formatting or normalization. "
        "Input format: the text string to convert",
        to_uppercase
    ),
    "ExtractNumbers": (
        "Find and extract all numbers from a text string. "
        "Use this to parse numeric data from mixed text. "
        "Input format: the text string to search for numbers in",
        extract_numbers
    ),
}


def get_basic_tools():
    """Get the basic tools dictionary for use with ReAct agent"""
    return BASIC_TOOLS
