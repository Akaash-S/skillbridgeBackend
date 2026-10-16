#!/usr/bin/env python3
"""
SkillBridge Database Backup & Disaster Recovery CLI.
Connects directly to BackupService to perform manual backups, list snapshots,
run dry-run integrity verifications, or restore to a past snapshot.
"""

import sys
import os
import argparse
import logging

# Ensure project root is on sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from app.services.backup_service import BackupService, BACKUP_COLLECTION
from firebase_admin import firestore

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('backup_cli')

def cmd_backup(args):
    """Trigger an encrypted full backup."""
    service = BackupService()
    print("Initiating full database backup...")
    service.perform_backup()
    print("Backup operation finished.")

def cmd_list(args):
    """List all available backup snapshots in Firestore."""
    service = BackupService()
    db = service.db
    if not db:
        print("Error: Firestore database instance unavailable.", file=sys.stderr)
        sys.exit(1)

    print(f"Fetching snapshots from '{BACKUP_COLLECTION}' collection...")
    docs = list(db.collection(BACKUP_COLLECTION).order_by('created_at', direction=firestore.Query.DESCENDING).stream())
    
    if not docs:
        print("No backup snapshots found.")
        return

    print(f"\nFound {len(docs)} snapshot(s):")
    print(f"{'Snapshot ID':<22} | {'Documents':<10} | {'Chunks':<8} | {'Status':<10} | {'Created At'}")
    print("-" * 75)
    for doc in docs:
        d = doc.to_dict()
        doc_count = d.get('doc_count', 'N/A')
        total_chunks = d.get('total_chunks', 'N/A')
        status = d.get('status', 'unknown')
        created_at = d.get('created_at', 'N/A')
        print(f"{doc.id:<22} | {str(doc_count):<10} | {str(total_chunks):<8} | {status:<10} | {str(created_at)}")
    print()

def cmd_restore(args):
    """Restore database from a specific snapshot."""
    timestamp = args.snapshot_id
    dry_run = args.dry_run
    
    if not dry_run:
        print(f"WARNING: This will overwrite documents in live collections with data from snapshot '{timestamp}'.")
        confirm = input("Are you absolutely sure you want to proceed? [type 'yes' to confirm]: ")
        if confirm.strip().lower() != 'yes':
            print("Restore aborted by user.")
            sys.exit(0)

    service = BackupService()
    success = service.restore_backup(timestamp, dry_run=dry_run)
    if success:
        mode = "Dry-run verification" if dry_run else "Restore"
        print(f"\n{mode} completed successfully for snapshot: {timestamp}")
    else:
        print(f"\nRestore operation failed for snapshot: {timestamp}", file=sys.stderr)
        sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="SkillBridge Backup & Restore CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # backup
    p_backup = subparsers.add_parser("backup", help="Perform immediate encrypted backup")
    p_backup.set_defaults(func=cmd_backup)

    # list
    p_list = subparsers.add_parser("list", help="List available snapshots")
    p_list.set_defaults(func=cmd_list)

    # restore
    p_restore = subparsers.add_parser("restore", help="Restore database from snapshot")
    p_restore.add_argument("snapshot_id", help="Timestamp snapshot ID (e.g. 20261016_110000)")
    p_restore.add_argument("--dry-run", action="store_true", help="Validate decryption and schema without mutating database")
    p_restore.set_defaults(func=cmd_restore)

    args = parser.parse_args()
    args.func(args)

if __name__ == "__main__":
    main()
