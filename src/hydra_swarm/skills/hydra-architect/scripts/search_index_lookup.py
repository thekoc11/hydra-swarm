"""Pure function for 4-tuple exact match against search_index.md.

State-machine parser that reads the structured markdown index file and returns
the entry dict when (query, freshness, endpoint, goggle) all match exactly.

Stdlib only. Importable. No CLI.
"""

import re
from pathlib import Path


def lookup(index_path: str, query: str, freshness: str, endpoint: str, goggle: str) -> dict | None:
    """Return {"S_id": "S{n}", "header": {...}, "body": "..."} on 4-tuple match, else None.

    Args:
        index_path: Path to search_index_<ts>.md file.
        query: Exact query string to match.
        freshness: Freshness value to match (e.g., 'pw', 'pm', 'py', 'none').
        endpoint: Endpoint value to match (e.g., 'web', 'news', 'llm').
        goggle: Goggle value to match (e.g., 'none', 'hydra-releases').

    Returns:
        dict with keys S_id, header, body on match; None if not found or file missing.
    """
    if not Path(index_path).exists():
        return None

    # State machine states
    SEEKING_HEADER = 1
    SEEKING_QUERY_LINE = 2
    COLLECTING_BODY = 3
    END = 4

    state = SEEKING_HEADER
    current_header: dict = {}
    current_s_id: str = ""
    current_query: str = ""
    current_body_lines: list[str] = []

    # Regex patterns
    s_header_re = re.compile(r"^(S\d+) \| (.+)$")

    try:
        with open(index_path, "r") as f:
            for line in f:
                line = line.rstrip("\n")

                if state == SEEKING_HEADER:
                    m = s_header_re.match(line)
                    if m:
                        s_id = m.group(1)
                        header_str = m.group(2)
                        # Parse pipe-delimited key=value pairs
                        header = {}
                        for part in header_str.split("|"):
                            part = part.strip()
                            if "=" in part:
                                key, _, value = part.partition("=")
                                header[key.strip()] = value.strip()
                        current_header = header
                        current_s_id = s_id
                        state = SEEKING_QUERY_LINE
                    continue

                elif state == SEEKING_QUERY_LINE:
                    if not line.strip():
                        continue
                    # Expect query: "..." line
                    if line.strip().startswith("query:"):
                        # Extract text between the first and last double quote
                        query_line = line.strip()
                        # Find the content between outer double quotes
                        # Format: query: "exact query string with \" escaped"
                        rest = query_line[len("query:"):].strip()
                        if rest.startswith('"') and rest.endswith('"'):
                            extracted = rest[1:-1]  # strip outer quotes
                            # Unescape \"
                            extracted = extracted.replace('\\"', '"')
                            current_query = extracted
                        else:
                            # Malformed query line - skip this entry
                            state = SEEKING_HEADER
                            continue

                        # Match check: compare 4-tuple
                        if (
                            current_query == query
                            and current_header.get("freshness") == freshness
                            and current_header.get("endpoint") == endpoint
                            and current_header.get("goggle") == goggle
                        ):
                            current_body_lines = []
                            state = COLLECTING_BODY
                        else:
                            # No match — skip to END
                            state = END
                    else:
                        # Expected query line but got something else — malformed, skip
                        state = SEEKING_HEADER
                    continue

                elif state == COLLECTING_BODY:
                    # Check for [END S{n}] — end of entry
                    end_match = re.match(r"^\[END S\d+\]$", line.strip())
                    if end_match:
                        # We've collected the full body
                        body = "\n".join(current_body_lines).strip()
                        return {
                            "S_id": current_s_id,
                            "header": current_header,
                            "body": body,
                        }

                    # Check for new S-header while in body (partial write / corrupt)
                    if s_header_re.match(line):
                        # Previous entry was corrupt — skip it, start parsing next
                        state = SEEKING_HEADER
                        # Re-process this line as a header
                        m = s_header_re.match(line)
                        if m:
                            s_id = m.group(1)
                            header_str = m.group(2)
                            header = {}
                            for part in header_str.split("|"):
                                part = part.strip()
                                if "=" in part:
                                    key, _, value = part.partition("=")
                                    header[key.strip()] = value.strip()
                            current_header = header
                            current_s_id = s_id
                            state = SEEKING_QUERY_LINE
                        continue

                    # Collect body line (skip separator lines like "---")
                    if line.strip() != "---":
                        current_body_lines.append(line)
                    continue

                elif state == END:
                    # Skip until next S-header or [END S{n}]
                    end_match = re.match(r"^\[END S\d+\]$", line.strip())
                    if end_match:
                        state = SEEKING_HEADER
                        continue
                    # New S-header encountered while skipping
                    if s_header_re.match(line):
                        m = s_header_re.match(line)
                        if m:
                            s_id = m.group(1)
                            header_str = m.group(2)
                            header = {}
                            for part in header_str.split("|"):
                                part = part.strip()
                                if "=" in part:
                                    key, _, value = part.partition("=")
                                    header[key.strip()] = value.strip()
                            current_header = header
                            current_s_id = s_id
                            state = SEEKING_QUERY_LINE
                    continue

    except (IOError, OSError):
        return None

    return None
