"""Environment-variable compatibility shim for the Odysseus -> Lodestar rename.

Lodestar's own environment variables use the ``LODESTAR_`` prefix. For every
variable that was previously named with the ``ODYSSEUS_`` prefix, this module
lets us keep reading the old name as a fallback so existing deployments (.env
files, docker-compose overrides, systemd units) keep working until users
migrate.

# TODO(lodestar): remove the ODYSSEUS_ fallback + warning once the legacy
# names have been deprecated for a full release cycle.
"""
import os
import warnings


def getenv(name: str, legacy_name: str, default: str | None = None) -> str | None:
    """Read *name*, falling back to the deprecated *legacy_name*.

    Returns ``default`` if neither is set. Emits a DeprecationWarning the
    first time the legacy name is used instead of the new one.
    """
    value = os.environ.get(name)
    if value is not None:
        return value
    legacy_value = os.environ.get(legacy_name)
    if legacy_value is not None:
        warnings.warn(
            f"{legacy_name} is deprecated; use {name} instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        return legacy_value
    return default
