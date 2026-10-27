"""
voting/chat_parser.py
─────────────────────
Stateless WhatsApp chat-export parser.

    parse_chat(raw_text) -> (messages, stats)

    messages : list of dicts, each:
        {"datetime": datetime, "author": str, "text": str, "is_media": bool}
    stats    : dict of counters describing what was parsed.

Mirrors the (data, stats) contract used by voting/dataset_cleaner.py so the
rest of the codebase sees a familiar shape. Nothing is mutated in place and no
database access happens here.

Supported export formats (English / en-US):
    Android : "1/1/24, 9:05 AM - Alice: message"
    iOS     : "[1/1/24, 9:05:00 AM] Alice: message"
Both 12-hour (AM/PM) and 24-hour clocks are accepted.
"""

import re
from datetime import datetime


# ─── Patrones (regex) que reconocen cada formato de WhatsApp ──────────────────
# A line that starts a new message looks like "<date>, <time> - <rest>" (Android)
# or "[<date>, <time>] <rest>" (iOS). Anything that does not match is treated as
# a continuation of the previous message (multi-line messages).
_TIME = r"\d{1,2}:\d{2}(?::\d{2})?(?:\s*[APap][Mm])?"   # 12h o 24h, con/sin segundos, con/sin AM/PM
_DATE = r"\d{1,2}/\d{1,2}/\d{2,4}"                       # día/mes 1-2 dígitos, año de 2 o 4 dígitos

_ANDROID_HEADER = re.compile(rf"^({_DATE}),\s+({_TIME})\s+-\s+(.*)$")   # "1/1/24, 9:05 AM - resto"
_IOS_HEADER = re.compile(rf"^\[({_DATE}),\s+({_TIME})\]\s+(.*)$")       # "[1/1/24, 9:05 AM] resto"

# Author / system split: a real message is "Author: text". System notices
# ("Messages and calls are end-to-end encrypted...") have no "author: " prefix.
# Es la ÚNICA señal que distingue un mensaje real de un aviso del sistema.
_AUTHOR_SPLIT = re.compile(r"^(?P<author>[^:\n]{1,60}):\s(?P<text>.*)$", re.DOTALL)

_MEDIA_MARKERS = ("<Media omitted>", "image omitted", "video omitted", "audio omitted")


# ─── Normalización y parseo de fecha/hora ──────────────────────────────────────
def _normalize_spaces(value: str) -> str:
    """Replace the narrow/regular no-break spaces WhatsApp injects around AM/PM."""
    # OJO: dentro de esta función hay espacios Unicode especiales (non-breaking /
    # narrow no-break) literales en el código, no espacios normales " " — son
    # justo los que WhatsApp inyecta y los que esta función limpia.
    return value.replace(" ", " ").replace(" ", " ")


def _parse_datetime(date_str: str, time_str: str):
    """Try several en-US date/time layouts; return a datetime or None."""
    combined = f"{date_str.strip()} {_normalize_spaces(time_str).strip().upper()}"
    combined = re.sub(r"\s+", " ", combined)
    date_formats = ("%m/%d/%y", "%m/%d/%Y")                            # año de 2 o 4 dígitos
    time_formats = ("%I:%M %p", "%I:%M:%S %p", "%H:%M", "%H:%M:%S")    # 12h/24h, con/sin segundos
    # Prueba las 2 x 4 = 8 combinaciones de formato hasta que alguna funcione.
    for dfmt in date_formats:
        for tfmt in time_formats:
            try:
                return datetime.strptime(combined, f"{dfmt} {tfmt}")
            except ValueError:
                continue
    return None  # ninguna combinación matcheó -> se cuenta como "unparsed" en parse_chat()


# ─── Detección de inicio de mensaje ────────────────────────────────────────────
def _match_header(line: str):
    """Return (date_str, time_str, rest) if the line starts a message, else None."""
    # Prueba primero Android, luego iOS. Si ninguno matchea, la línea no es un
    # timestamp -> parse_chat() la tratará como continuación de un mensaje previo.
    match = _ANDROID_HEADER.match(line) or _IOS_HEADER.match(line)
    if match:
        return match.group(1), match.group(2), match.group(3)
    return None


# ─── Función principal: parse_chat() ───────────────────────────────────────────
def parse_chat(raw_text: str):
    """Parse a raw WhatsApp export into structured messages plus parse stats."""
    messages = []
    stats = {
        "total_lines": 0,
        "parsed_messages": 0,
        "system_lines": 0,
        "media_messages": 0,
        "continuation_lines": 0,
        "unparsed_lines": 0,
    }

    if not raw_text:
        return messages, stats   # caso límite: texto vacío, no explota

    lines = raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\n")

    for raw_line in lines:
        line = raw_line.rstrip()
        if not line.strip():
            continue
        stats["total_lines"] += 1

        # Paso 1: ¿esta línea arranca un mensaje nuevo (tiene timestamp)?
        header = _match_header(line)
        if header is None:
            # Continuation of the previous message (multi-line body).
            # No tiene timestamp -> se pega al mensaje anterior con "\n".
            if messages:
                messages[-1]["text"] += "\n" + line
                stats["continuation_lines"] += 1
            else:
                stats["unparsed_lines"] += 1
            continue

        # Paso 2: ¿tiene forma "Autor: texto", o es un aviso del sistema?
        date_str, time_str, rest = header
        author_match = _AUTHOR_SPLIT.match(rest)
        if not author_match:
            # Header with no "author: " prefix -> system notice.
            stats["system_lines"] += 1
            continue

        # Paso 3: convertir el string de fecha/hora a un datetime real.
        dt = _parse_datetime(date_str, time_str)
        if dt is None:
            stats["unparsed_lines"] += 1
            continue

        # Paso 4: marcar si es multimedia. Cuenta para la frecuencia, pero
        # chat_sentiment.py lo excluye del análisis de sentimiento.
        text = author_match.group("text").strip()
        is_media = any(marker.lower() in text.lower() for marker in _MEDIA_MARKERS)
        if is_media:
            stats["media_messages"] += 1

        # Paso 5: ya validado -> se agrega como mensaje estructurado.
        messages.append({
            "datetime": dt,
            "author": author_match.group("author").strip(),
            "text": text,
            "is_media": is_media,
        })
        stats["parsed_messages"] += 1

    return messages, stats
