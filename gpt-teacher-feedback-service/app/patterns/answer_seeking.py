"""Padrões em português para detectar pedido de resposta pronta.

Edite esta lista livremente — ela é carregada em tempo de import e compilada
uma única vez. Cada item é uma regex case-insensitive.
"""
import re
from typing import NamedTuple


class Pattern(NamedTuple):
    name: str
    regex: re.Pattern


_RAW_PATTERNS: list[tuple[str, str]] = [
    # Pedido direto de resposta
    ("me_da_resposta",        r"me\s+d[aá]\s+a\s+resposta"),
    ("pode_dar_resposta",     r"pode\s+(me\s+)?dar\s+a\s+resposta"),
    ("qual_resposta",         r"qual\s+[eé]\s+a\s+resposta"),
    ("qual_resposta2",        r"qual\s+a\s+resposta"),
    ("me_fala_resposta",      r"me\s+fala\s+a\s+resposta"),
    ("me_manda_resposta",     r"me\s+manda\s+a\s+resposta"),
    ("me_passa_resposta",     r"me\s+pass[ae]\s+a\s+resposta"),
    ("so_me_da_resposta",     r"s[oó]\s+me\s+d[aá]\s+a\s+resposta"),
    ("da_logo_resposta",      r"d[aá]\s+(logo\s+)?a\s+resposta"),
    # Pedido de solução
    ("da_solucao",            r"me\s+d[aá]\s+a\s+solu[cç][aã]o"),
    ("pode_dar_solucao",      r"pode\s+(me\s+)?dar\s+a\s+solu[cç][aã]o"),
    ("qual_solucao",          r"qual\s+[eé]\s+a\s+solu[cç][aã]o"),
    ("me_passa_solucao",      r"me\s+pass[ae]\s+a\s+solu[cç][aã]o"),
    # Pedido de código
    ("me_da_codigo",          r"me\s+d[aá]\s+o\s+c[oó]digo"),
    ("manda_codigo_completo", r"manda\s+o\s+c[oó]digo\s+completo"),
    ("so_passa_codigo",       r"s[oó]\s+me\s+passa\s+o\s+c[oó]digo"),
    ("me_passa_codigo",       r"me\s+pass[ae]\s+o\s+c[oó]digo"),
    ("mostra_codigo_completo",r"mostra\s+o\s+c[oó]digo\s+completo"),
    ("qual_codigo",           r"qual\s+[eé]\s+o\s+c[oó]digo"),
    ("me_manda_codigo",       r"me\s+manda\s+o\s+c[oó]digo"),
    ("pode_dar_codigo",       r"pode\s+(me\s+)?dar\s+o\s+c[oó]digo"),
    ("escreve_o_codigo",      r"escreve\s+o\s+c[oó]digo"),
    # Fazer por mim
    ("faz_pra_mim",           r"faz\s+pra\s+mim"),
    ("faz_por_mim",           r"faz\s+por\s+mim"),
    ("resolve_pra_mim",       r"resolve\s+(pra|por)\s+mim"),
    ("resolve_isso",          r"resolve\s+isso"),
    ("escreve_pra_mim",       r"escreve\s+pra\s+mim"),
    ("digita_pra_mim",        r"digita\s+pra\s+mim"),
    ("faz_isso_pra_mim",      r"faz\s+isso\s+(pra|por)\s+mim"),
    ("pode_resolver",         r"pode\s+(você\s+)?resolver\s+(por\s+mim|isso)"),
    # Só fazer / só dar
    ("so_faz",                r"s[oó]\s+faz\s+(isso|o\s+c[oó]digo|pra\s+mim)"),
    ("so_da",                 r"s[oó]\s+d[aá]\s+(a\s+resposta|o\s+c[oó]digo|a\s+solu[cç][aã]o)"),
]

PATTERNS: list[Pattern] = [
    Pattern(name=name, regex=re.compile(raw, re.IGNORECASE))
    for name, raw in _RAW_PATTERNS
]


def find_answer_seeking_pattern(text: str) -> Pattern | None:
    """Retorna o primeiro padrão que casar, ou None."""
    for pattern in PATTERNS:
        if pattern.regex.search(text):
            return pattern
    return None
