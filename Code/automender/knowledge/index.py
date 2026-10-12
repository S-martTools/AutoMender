from __future__ import annotations

import json
import sqlite3
import xml.etree.ElementTree as ET
import zipfile
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..data.solidity import normalize_tokens
from ..taxonomy import BUG_TO_EXPERT, normalize_bug_type
from ..utils import iter_files, sha256_bytes


SCHEMA = """
CREATE TABLE IF NOT EXISTS documents (
 id INTEGER PRIMARY KEY, kind TEXT NOT NULL, source TEXT NOT NULL,
 bug_type TEXT NOT NULL DEFAULT '', category TEXT NOT NULL DEFAULT '',
 token_hash TEXT NOT NULL UNIQUE, content TEXT NOT NULL, metadata TEXT NOT NULL DEFAULT '{}'
);
CREATE VIRTUAL TABLE IF NOT EXISTS documents_fts USING fts5(content, bug_type, category, content='documents', content_rowid='id');
CREATE TRIGGER IF NOT EXISTS documents_ai AFTER INSERT ON documents BEGIN
 INSERT INTO documents_fts(rowid, content, bug_type, category) VALUES (new.id, new.content, new.bug_type, new.category);
END;
"""


class KnowledgeIndex:
    def __init__(self, path: str):
        self.path = path

    def search(self, query: str, bug_types: Sequence[str] = (), limit: int = 5) -> List[Dict[str, Any]]:
        terms = [token.replace('"', '') for token in query.split() if token][:20]
        fts = " OR ".join('"%s"' % term for term in terms) or '"contract"'
        normalized = [normalize_bug_type(item) for item in bug_types]
        connection = sqlite3.connect(self.path)
        connection.row_factory = sqlite3.Row
        try:
            rows = connection.execute(
                "SELECT d.*, bm25(documents_fts) AS score FROM documents_fts "
                "JOIN documents d ON d.id=documents_fts.rowid WHERE documents_fts MATCH ? "
                "ORDER BY CASE WHEN d.bug_type IN (%s) THEN 0 ELSE 1 END, score LIMIT ?" % (",".join("?" for _ in normalized) or "''"),
                [fts] + normalized + [limit],
            ).fetchall()
            return [dict(row) for row in rows]
        finally:
            connection.close()


def _xlsx_rows(path: str) -> Iterable[List[str]]:
    namespace = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as archive:
        shared: List[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
            shared = ["".join(node.text or "" for node in item.findall(".//x:t", namespace)) for item in root.findall("x:si", namespace)]
        for sheet in sorted(name for name in archive.namelist() if name.startswith("xl/worksheets/sheet") and name.endswith(".xml")):
            root = ET.fromstring(archive.read(sheet))
            for row in root.findall(".//x:row", namespace):
                values: List[str] = []
                for cell in row.findall("x:c", namespace):
                    value_node = cell.find("x:v", namespace)
                    inline = cell.find("x:is/x:t", namespace)
                    value = value_node.text if value_node is not None else (inline.text if inline is not None else "")
                    if cell.get("t") == "s" and value:
                        value = shared[int(value)]
                    values.append(value or "")
                if any(values):
                    yield values


def build_index(output_path: str, semantic_dir: Optional[str] = None, knowledge_jsonl: Optional[str] = None, bug_description_xlsx: Optional[str] = None) -> Dict[str, int]:
    target = Path(output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(str(target))
    try:
        connection.executescript(SCHEMA)
        inserted = duplicate = 0
        def add(kind: str, source: str, content: str, bug_type: str = "", category: str = "", metadata: Optional[Dict[str, Any]] = None) -> None:
            nonlocal inserted, duplicate
            digest = sha256_bytes(normalize_tokens(content).encode())
            try:
                connection.execute(
                    "INSERT INTO documents(kind,source,bug_type,category,token_hash,content,metadata) VALUES(?,?,?,?,?,?,?)",
                    (kind, source, bug_type, category, digest, content, json.dumps(metadata or {}, ensure_ascii=False)),
                )
                inserted += 1
            except sqlite3.IntegrityError:
                duplicate += 1
        if knowledge_jsonl:
            for line in Path(knowledge_jsonl).read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    add("repair_knowledge", row.get("source", knowledge_jsonl), row.get("content", ""), row.get("bug_type", ""), row.get("category", ""), row)
        if bug_description_xlsx:
            rows = list(_xlsx_rows(bug_description_xlsx))
            for index, row in enumerate(rows[1:] if len(rows) > 1 else rows):
                content = "\n".join(value for value in row if value)
                bug_type = ""
                for candidate in row[:3]:
                    try:
                        bug_type = normalize_bug_type(candidate)
                        break
                    except ValueError:
                        pass
                category = BUG_TO_EXPERT.get(bug_type, "")
                add("repair_knowledge", "%s#row%d" % (bug_description_xlsx, index + 2), content, bug_type=bug_type, category=category, metadata={"row": row})
        if semantic_dir:
            root = Path(semantic_dir)
            for path in iter_files(root, ".sol"):
                add("semantic_contract", str(path.relative_to(root)), path.read_text(encoding="utf-8", errors="replace"))
        connection.commit()
        return {"inserted": inserted, "duplicates_folded": duplicate}
    finally:
        connection.close()
