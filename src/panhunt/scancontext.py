from __future__ import annotations

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
    max_attachment_size: int = 1_073_741_824
    max_attachments_per_message: int = 1_000
    max_total_attachment_bytes: int = 1_073_741_824
    max_path_length: int = 4096


class ResourceBudget:
    """Shared scan budget for nested/container-created jobs."""

    def __init__(self, limits: ScanLimits) -> None:
        self.limits = limits
        self._child_jobs = 0
        self._expanded_bytes = 0
        self._attachment_bytes = 0
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

    def reserve_expanded(self, logical_path: str, byte_count: int) -> None:
        if byte_count <= 0:
            return
        with self._lock:
            if self._expanded_bytes + byte_count > self.limits.max_total_expanded_bytes:
                raise PANHuntException(
                    f'Scan expanded-byte limit exceeded for "{logical_path}": '
                    f'{panutils.size_friendly(size=self._expanded_bytes + byte_count)} over '
                    f'{panutils.size_friendly(size=self.limits.max_total_expanded_bytes)}'
                )
            self._expanded_bytes += byte_count

    def reserve_attachment(self, logical_path: str, byte_count: int, attachment_count: int = 1) -> None:
        if attachment_count > self.limits.max_attachments_per_message:
            raise PANHuntException(
                f'Attachment count limit exceeded for "{logical_path}": '
                f'{attachment_count} over {self.limits.max_attachments_per_message}'
            )
        if byte_count > self.limits.max_attachment_size:
            raise PANHuntException(
                f'Attachment size limit exceeded for "{logical_path}": '
                f'{panutils.size_friendly(size=byte_count)} over '
                f'{panutils.size_friendly(size=self.limits.max_attachment_size)}'
            )
        if byte_count <= 0:
            return
        with self._lock:
            if self._attachment_bytes + byte_count > self.limits.max_total_attachment_bytes:
                raise PANHuntException(
                    f'Scan decoded attachment-byte limit exceeded for "{logical_path}": '
                    f'{panutils.size_friendly(size=self._attachment_bytes + byte_count)} over '
                    f'{panutils.size_friendly(size=self.limits.max_total_attachment_bytes)}'
                )
            self._attachment_bytes += byte_count

    @property
    def child_jobs(self) -> int:
        with self._lock:
            return self._child_jobs

    @property
    def expanded_bytes(self) -> int:
        with self._lock:
            return self._expanded_bytes

    @property
    def attachment_bytes(self) -> int:
        with self._lock:
            return self._attachment_bytes


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

    def reserve_attachment(self, basename: str, byte_count: int, attachment_count: int = 1) -> None:
        logical_path = f'{self.logical_path}!/{basename}'
        self.budget.reserve_attachment(
            logical_path=logical_path,
            byte_count=byte_count,
            attachment_count=attachment_count
        )

    def child(self, basename: str, payload_size: int = 0) -> 'ScanContext':
        logical_path = f'{self.logical_path}!/{basename}'
        depth = self.depth + 1
        if len(logical_path) > self.budget.limits.max_path_length:
            raise PANHuntException(
                f'Scan path length limit exceeded for "{logical_path}": '
                f'{len(logical_path)} over {self.budget.limits.max_path_length}'
            )
        self.budget.reserve_child(logical_path=logical_path, depth=depth, payload_size=payload_size)
        return ScanContext(
            logical_path=logical_path,
            depth=depth,
            budget=self.budget,
            parent_archive=self.logical_path,
            container_chain=[*self.container_chain, self.logical_path]
        )
