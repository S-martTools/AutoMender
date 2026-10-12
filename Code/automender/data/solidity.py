from __future__ import annotations

import re
from typing import Iterator, List, Union


TOKEN_RE = re.compile(
    r'''"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[A-Za-z_$][A-Za-z0-9_$]*'''
    r'''|0[xX][0-9A-Fa-f_]+|(?:\d[\d_]*)(?:\.[\d_]*)?(?:[eE][+-]?[\d_]+)?'''
    r'''|(?:>>=|<<=|\*\*|=>|==|!=|<=|>=|&&|\|\||\+\+|--|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<|>>|->)|.''',
    re.DOTALL,
)


def normalize_text(data: Union[bytes, str]) -> str:
    if isinstance(data, bytes):
        text = data.decode("utf-8-sig", errors="replace")
    else:
        text = data[1:] if data.startswith("\ufeff") else data
    return text.replace("\r\n", "\n").replace("\r", "\n")


def strip_comments(text: str) -> str:
    output: List[str] = []
    index = 0
    while index < len(text):
        char = text[index]
        if char in "\"'":
            quote = char
            output.append(char)
            index += 1
            while index < len(text):
                output.append(text[index])
                if text[index] == "\\" and index + 1 < len(text):
                    index += 1
                    output.append(text[index])
                elif text[index] == quote:
                    index += 1
                    break
                index += 1
            continue
        if text.startswith("//", index):
            newline = text.find("\n", index + 2)
            index = len(text) if newline < 0 else newline
            continue
        if text.startswith("/*", index):
            end = text.find("*/", index + 2)
            index = len(text) if end < 0 else end + 2
            continue
        output.append(char)
        index += 1
    return "".join(output)


def solidity_tokens(text: str) -> List[str]:
    clean = strip_comments(normalize_text(text))
    return [match.group(0) for match in TOKEN_RE.finditer(clean) if not match.group(0).isspace()]


def normalize_tokens(text: str) -> str:
    return "\0".join(solidity_tokens(text))


def token_windows(tokens: List[str], size: int) -> Iterator[List[str]]:
    for index in range(max(0, len(tokens) - size + 1)):
        yield tokens[index:index + size]
