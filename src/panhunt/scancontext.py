import threading
from dataclasses import dataclass
from typing import Optional

from . import panutils
from .exceptions import PANHuntException


@dataclass(frozen=True)
class ScanLimits:
    max_depth: int
    max_child_jobs: int
    max_total_expanded_bytes: int


class ResourceBudget:
    """Shared scan budget for nested/container-created jobs."""

    def __init__(self, limits: ScanLimits) -> None:
        self.limits = limits
        self._child_jobs = 0
        self._expanded_bytes = 0
        self._lock = threading.Lock()

    def reserve_child(self, logical_path: str, depth: int, payload_size: int = 0) -> None:
        with self._lock:
            if depth > self.limits.max_depth:
                raise PANHuntException(
                    f'Scan depth limit exceeded for "{logical_path}": '
                    f'{depth} over {self.limits.max_depth}'
                )

            if self._child_jobs + 1 > self.limits.max_child_jobs:
                raise PANHuntException(
                    f'Scan child-job limit exceeded for "{logical_path}": '
                    f'{self._child_jobs + 1} over {self.limits.max_child_jobs}'
                )

            if self._expanded_bytes + payload_size > self.limits.max_total_expanded_bytes:
                raise PANHuntException(
                    f'Scan expanded-byte limit exceeded for "{logical_path}": '
                    f'{panutils.size_friendly(size=self._expanded_bytes + payload_size)} over '
                    f'{panutils.size_friendly(size=self.limits.max_total_expanded_bytes)}'
                )

            self._child_jobs += 1
            self._expanded_bytes += payload_size

    @property
    def child_jobs(self) -> int:
        with self._lock:
            return self._child_jobs

    @property
    def expanded_bytes(self) -> int:
        with self._lock:
            return self._expanded_bytes


class ScanContext:
    """Per-job scan metadata backed by a shared ResourceBudget."""

    def __init__(
            self,
            *,
            logical_path: str,
            depth: int,
            budget: ResourceBudget,
            parent_archive: Optional[str] = None,
            container_chain: Optional[list[str]] = None) -> None:
        self.logical_path = logical_path
        self.depth = depth
        self.parent_archive = parent_archive
        self.container_chain = list(container_chain or [])
        self.budget = budget

    @classmethod
    def root(
            cls,
            logical_path: str,
            limits: ScanLimits,
            budget: Optional[ResourceBudget] = None) -> 'ScanContext':
        return cls(
            logical_path=logical_path,
            depth=0,
            budget=budget if budget else ResourceBudget(limits),
            parent_archive=None,
            container_chain=[]
        )

    def child(self, basename: str, payload_size: int = 0) -> 'ScanContext':
        logical_path = f'{self.logical_path}!/{basename}'
        depth = self.depth + 1
        self.budget.reserve_child(logical_path=logical_path, depth=depth, payload_size=payload_size)
        return ScanContext(
            logical_path=logical_path,
            depth=depth,
            budget=self.budget,
            parent_archive=self.logical_path,
            container_chain=[*self.container_chain, self.logical_path]
        )
