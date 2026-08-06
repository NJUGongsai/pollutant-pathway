"""P4-T8 immutable run store (final_design §21, ADR-0006).

- Completed/frozen runs cannot be mutated in place;
- child runs preserve the parent identity and never overwrite the parent
  result; an existing child id is rejected (never overwritten);
- ``verify_result_hash`` recomputes the expected hash to detect an altered
  manifest;
- P4-R1-E: the store keeps an immutable canonical snapshot (deep copy) and
  public getters return read-only copies — mutating a returned manifest can
  never change the internal state.
"""
from __future__ import annotations

from reaction_agent.schemas.p4.run import (
    ImmutableRunManifest,
    RunFreezeState,
)
from reaction_agent.runtime.manifest import recompute_result_hash


class RunAlreadyFrozenError(Exception):
    """Raised when mutating a frozen run."""


class RunNotFoundError(KeyError):
    """Raised when a run_id is not present in the store."""


class RunHashMismatchError(ValueError):
    """Raised when a stored result hash does not match the recomputed one."""


class RuntimeRun:
    """An immutable run; the manifest is never mutated in place."""

    def __init__(self, manifest: ImmutableRunManifest):
        # Deep-copy canonical snapshot: the caller's object is never held.
        self._manifest = manifest.model_copy(deep=True)

    @property
    def manifest(self) -> ImmutableRunManifest:
        """Return a read-only copy; mutating it cannot affect internal state."""
        return self._manifest.model_copy(deep=True)

    @property
    def freeze_state(self) -> RunFreezeState:
        return self._manifest.freeze_state

    @property
    def result_hash(self) -> str:
        return self._manifest.result_hash

    @property
    def parent_run_id(self) -> str | None:
        return self._manifest.parent_run_id

    def verify(self) -> str:
        """Recompute and compare the result hash. Returns the recomputed hash."""
        recomputed = recompute_result_hash(self._manifest)
        if recomputed != self._manifest.result_hash:
            raise RunHashMismatchError(
                f"run {self._manifest.run_id} result hash mismatch: "
                f"stored={self._manifest.result_hash[:16]}... "
                f"recomputed={recomputed[:16]}...")
        return recomputed


class ImmutableRunStore:
    """In-memory immutable run store keyed by run_id."""

    def __init__(self):
        self._runs: dict[str, RuntimeRun] = {}

    def create(self, manifest: ImmutableRunManifest) -> RuntimeRun:
        if manifest.run_id in self._runs:
            raise ValueError(f"run already exists: {manifest.run_id}")
        run = RuntimeRun(manifest)
        # P4-R1-E: verify the hash before accepting the run.
        run.verify()
        self._runs[manifest.run_id] = run
        return run

    def get(self, run_id: str) -> RuntimeRun:
        if run_id not in self._runs:
            raise RunNotFoundError(f"run not found: {run_id}")
        return self._runs[run_id]

    def freeze(self, run_id: str) -> RuntimeRun:
        run = self.get(run_id)
        frozen = run.manifest.model_copy(
            update={"freeze_state": RunFreezeState.frozen})
        self._runs[run_id] = RuntimeRun(frozen)
        return self._runs[run_id]

    def mutate(self, run_id: str, updates: dict) -> RuntimeRun:
        run = self.get(run_id)
        if run.freeze_state == RunFreezeState.frozen:
            raise RunAlreadyFrozenError(
                f"cannot mutate frozen run {run_id}")
        mutated = run.manifest.model_copy(update=updates)
        self._runs[run_id] = RuntimeRun(mutated)
        return self._runs[run_id]

    def create_child(self, parent_id: str, child_id: str,
                     updates: dict) -> ImmutableRunManifest:
        """Create a child run that preserves the parent identity.

        The child's ``result_hash`` is recomputed from its own content so the
        child is content-addressed and integrity-checkable (a stale inherited
        hash would make the child unverifiable). An existing child id is
        rejected — never overwritten (P4-R1-E).
        """
        if child_id in self._runs:
            raise ValueError(f"child run already exists: {child_id}")
        parent = self.get(parent_id)
        child = parent.manifest.model_copy(update={
            **updates,
            "run_id": child_id,
            "parent_run_id": parent_id,
            "freeze_state": RunFreezeState.active,
        })
        child = child.model_copy(update={"result_hash": recompute_result_hash(child)})
        self._runs[child_id] = RuntimeRun(child)
        return child

    def verify(self, run_id: str) -> str:
        return self.get(run_id).verify()

    def __contains__(self, run_id: str) -> bool:
        return run_id in self._runs