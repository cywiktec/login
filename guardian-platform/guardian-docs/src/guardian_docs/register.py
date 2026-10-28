"""Controlled document register shared by `nza` and `ukdp`."""

from dataclasses import dataclass

from .markdown import table

STATUSES = ("draft", "review", "approved", "obsolete")
_NEXT = {"draft": {"review"}, "review": {"draft", "approved"}, "approved": {"obsolete"}, "obsolete": set()}


@dataclass(frozen=True)
class Document:
    id: str
    title: str
    owner: str
    version: str = "0.1"
    status: str = "draft"

    def __post_init__(self):
        if not (self.id and self.title and self.owner):
            raise ValueError("id, title and owner are required")
        if self.status not in STATUSES:
            raise ValueError(f"bad status: {self.status!r}")


class Register:
    def __init__(self, name):
        self.name = name
        self._docs = {}

    def add(self, doc):
        if doc.id in self._docs:
            raise ValueError(f"duplicate id {doc.id}")
        self._docs[doc.id] = doc

    def get(self, doc_id):
        return self._docs[doc_id]

    def transition(self, doc_id, status, approver=None):
        """Status changes follow draft -> review -> approved -> obsolete; approval needs an
        approver other than the owner."""
        doc = self._docs[doc_id]
        if status not in _NEXT[doc.status]:
            raise ValueError(f"{doc.status} -> {status} not allowed")
        if status == "approved" and (not approver or approver == doc.owner):
            raise PermissionError("approval needs an approver different from the owner")
        self._docs[doc_id] = Document(doc.id, doc.title, doc.owner, doc.version, status)

    def render(self):
        return f"# {self.name}\n\n" + table(
            ["ID", "Title", "Owner", "Version", "Status"],
            [(d.id, d.title, d.owner, d.version, d.status) for d in sorted(self._docs.values(), key=lambda d: d.id)])
