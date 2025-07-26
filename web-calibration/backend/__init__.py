"""Backend package init

This file ensures that **legacy absolute imports** like `import db.storage_service` or
`from db.database import get_db` still resolve to the *same* modules that live
under the fully–qualified package name ``backend.db``.

Without this bridge we would end up with two parallel copies of the database
singletons – one under ``backend.db`` (used during application startup) and
another under the top-level name ``db`` (used by strongly-typed or older
scripts). That duplication caused the infamous *"Database pool not
initialized"* error because the storage service was talking to the copy that
never received `init_pool()`.
"""

import importlib
import sys


# ---------------------------------------------------------------------------
# Expose `backend.db` as `db` to the import system.
# ---------------------------------------------------------------------------

# Import sub-packages once using their canonical names
_db_pkg = importlib.import_module(__name__ + ".db")
_database_mod = importlib.import_module(__name__ + ".db.database")
_storage_mod = importlib.import_module(__name__ + ".db.storage_service")

# Register aliases so ``import db`` and ``import db.storage_service`` resolve
sys.modules.setdefault("db", _db_pkg)
sys.modules.setdefault("db.database", _database_mod)
sys.modules.setdefault("db.storage_service", _storage_mod)

# Clean up the temporary names
del importlib, sys, _db_pkg, _database_mod, _storage_mod
