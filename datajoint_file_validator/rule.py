from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional
from .constraint import Constraint, CONSTRAINT_MAP
from .result import ValidationResult
from .snapshot import Snapshot, PathLike, FileMetadata
from .query import Query, GlobQuery
from .config import config
from .error import DJFileValidatorError
from .hash_utils import generate_id


@dataclass
class Rule:
    """A single rule for a fileset."""

    id: Optional[str]
    description: Optional[str]
    constraints: List[Constraint] = field(default_factory=list)
    query: Query = field(default_factory=GlobQuery)

    def __post_init__(self):
        if not self.id:
            self.id = generate_id(self)

    def __hash__(self):
        return hash((self.id, self.query, tuple(self.constraints)))

    def validate(self, snapshot: Snapshot) -> Dict[str, ValidationResult]:
        filtered_snapshot: Snapshot = self.query.filter(snapshot)
        if self.query.path == config.default_query and config.debug:
            assert filtered_snapshot == snapshot
        results = list(
            map(
                lambda constraint: constraint.validate(filtered_snapshot),
                self.constraints,
            )
        )
        return {
            constraint.name: result
            for constraint, result in zip(self.constraints, results)
        }

    @staticmethod
    def compile_query(raw: Any) -> "Query":
        assert isinstance(raw, str)
        return GlobQuery(path=raw)

    @staticmethod
    def compile_constraint(name: str, val: Any) -> "Constraint":
        if name not in CONSTRAINT_MAP:
            raise DJFileValidatorError(f"Unknown constraint: {name}")
        try:
            return CONSTRAINT_MAP[name](val)
        except DJFileValidatorError as e:
            raise DJFileValidatorError(f"Error parsing constraint {name}: {e}")

    @classmethod
    def from_dict(cls, d: Dict) -> "Rule":
        """Load a rule from a dictionary."""
        rest = {
            k: v
            for k, v in d.items()
            if k not in ("id", "description", "query", "constraints")
        }
        try:
            self_ = cls(
                id=d.get("id"),
                description=d.get("description"),
                query=cls.compile_query(d.get("query", config.default_query)),
                constraints=[
                    cls.compile_constraint(name, val) for name, val in rest.items()
                ],
            )
        except DJFileValidatorError as e:
            raise DJFileValidatorError(f"Error parsing rule '{id}': {e}")
        return self_
