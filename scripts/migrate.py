#!/usr/bin/env python3
"""Database migration management script.

This script provides commands for managing database migrations using Alembic.
"""

import sys
import argparse
import subprocess
from pathlib import Path
from typing import Optional

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))


class MigrationManager:
    """Manage database migrations."""
    
    def __init__(self):
        self.alembic_ini = project_root / "infra" / "migrations" / "alembic.ini"
        
    def run_alembic(self, command: str, *args) -> int:
        """Run an alembic command."""
        cmd = ["alembic", "-c", str(self.alembic_ini), command] + list(args)
        print(f"Running: {' '.join(cmd)}")
        return subprocess.call(cmd)
    
    def init(self) -> int:
        """Initialize migration environment."""
        print("Initializing migration environment...")
        return self.run_alembic("init", "infra/migrations")
    
    def create(self, message: str) -> int:
        """Create a new migration."""
        print(f"Creating migration: {message}")
        return self.run_alembic("revision", "--autogenerate", "-m", message)
    
    def upgrade(self, revision: str = "head") -> int:
        """Upgrade database to a revision."""
        print(f"Upgrading database to {revision}...")
        return self.run_alembic("upgrade", revision)
    
    def downgrade(self, revision: str) -> int:
        """Downgrade database to a revision."""
        print(f"Downgrading database to {revision}...")
        return self.run_alembic("downgrade", revision)
    
    def current(self) -> int:
        """Show current revision."""
        print("Current database revision:")
        return self.run_alembic("current")
    
    def history(self, verbose: bool = False) -> int:
        """Show migration history."""
        print("Migration history:")
        args = ["--verbose"] if verbose else []
        return self.run_alembic("history", *args)
    
    def heads(self) -> int:
        """Show current head revisions."""
        print("Head revisions:")
        return self.run_alembic("heads")
    
    def branches(self) -> int:
        """Show branch points."""
        print("Branch points:")
        return self.run_alembic("branches")
    
    def show(self, revision: str) -> int:
        """Show a specific revision."""
        print(f"Showing revision {revision}:")
        return self.run_alembic("show", revision)
    
    def stamp(self, revision: str) -> int:
        """Stamp database with a revision without running migrations."""
        print(f"Stamping database with revision {revision}...")
        return self.run_alembic("stamp", revision)
    
    def verify(self) -> int:
        """Verify migration status and integrity."""
        print("Verifying migration status...")
        
        # Check current revision
        result = self.current()
        if result != 0:
            print("ERROR: Failed to get current revision")
            return result
        
        # Check for pending migrations
        result = subprocess.call([
            "alembic", "-c", str(self.alembic_ini),
            "check"
        ])
        
        if result == 0:
            print("✓ Database schema is up to date")
        else:
            print("⚠ Database schema needs migration")
        
        return result


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Database migration management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create a new migration
  python scripts/migrate.py create "add user table"
  
  # Upgrade to latest
  python scripts/migrate.py upgrade
  
  # Upgrade to specific revision
  python scripts/migrate.py upgrade 001
  
  # Downgrade one revision
  python scripts/migrate.py downgrade -1
  
  # Show current revision
  python scripts/migrate.py current
  
  # Show migration history
  python scripts/migrate.py history
  
  # Verify migration status
  python scripts/migrate.py verify
        """
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Migration commands")
    
    # Init command
    subparsers.add_parser("init", help="Initialize migration environment")
    
    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new migration")
    create_parser.add_argument("message", help="Migration message")
    
    # Upgrade command
    upgrade_parser = subparsers.add_parser("upgrade", help="Upgrade database")
    upgrade_parser.add_argument(
        "revision", 
        nargs="?", 
        default="head",
        help="Target revision (default: head)"
    )
    
    # Downgrade command
    downgrade_parser = subparsers.add_parser("downgrade", help="Downgrade database")
    downgrade_parser.add_argument("revision", help="Target revision")
    
    # Current command
    subparsers.add_parser("current", help="Show current revision")
    
    # History command
    history_parser = subparsers.add_parser("history", help="Show migration history")
    history_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Verbose output"
    )
    
    # Heads command
    subparsers.add_parser("heads", help="Show head revisions")
    
    # Branches command
    subparsers.add_parser("branches", help="Show branch points")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show a specific revision")
    show_parser.add_argument("revision", help="Revision to show")
    
    # Stamp command
    stamp_parser = subparsers.add_parser("stamp", help="Stamp database with revision")
    stamp_parser.add_argument("revision", help="Revision to stamp")
    
    # Verify command
    subparsers.add_parser("verify", help="Verify migration status")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return 1
    
    manager = MigrationManager()
    
    # Execute command
    if args.command == "init":
        return manager.init()
    elif args.command == "create":
        return manager.create(args.message)
    elif args.command == "upgrade":
        return manager.upgrade(args.revision)
    elif args.command == "downgrade":
        return manager.downgrade(args.revision)
    elif args.command == "current":
        return manager.current()
    elif args.command == "history":
        return manager.history(args.verbose)
    elif args.command == "heads":
        return manager.heads()
    elif args.command == "branches":
        return manager.branches()
    elif args.command == "show":
        return manager.show(args.revision)
    elif args.command == "stamp":
        return manager.stamp(args.revision)
    elif args.command == "verify":
        return manager.verify()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())