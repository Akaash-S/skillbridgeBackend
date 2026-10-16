#!/bin/bash
# SkillBridge Consolidated Backup & Disaster Recovery Script
# Usage:
#   ./scripts/backup-restore.sh backup
#   ./scripts/backup-restore.sh list
#   ./scripts/backup-restore.sh dry-run <SNAPSHOT_ID>
#   ./scripts/backup-restore.sh restore <SNAPSHOT_ID>

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$ROOT_DIR"

COMMAND=${1:-""}
SNAPSHOT_ID=${2:-""}

print_usage() {
    echo "Usage: ./scripts/backup-restore.sh [backup | list | dry-run <SNAPSHOT_ID> | restore <SNAPSHOT_ID>]"
    echo ""
    echo "Commands:"
    echo "  backup               Run an immediate encrypted backup across all Firestore collections"
    echo "  list                 List all available backup snapshots stored in system_backups"
    echo "  dry-run <ID>         Validate decryption and verify document counts without modifying database"
    echo "  restore <ID>         Perform full database restore/rollback from snapshot"
}

if [ -z "$COMMAND" ]; then
    print_usage
    exit 1
fi

case "$COMMAND" in
    backup)
        echo "🚀 Running manual backup..."
        python scripts/backup_cli.py backup
        ;;
    list)
        echo "📋 Listing backup snapshots..."
        python scripts/backup_cli.py list
        ;;
    dry-run)
        if [ -z "$SNAPSHOT_ID" ]; then
            echo "❌ Error: Please specify a snapshot ID for dry-run."
            print_usage
            exit 1
        fi
        echo "🔍 Running dry-run validation for snapshot: $SNAPSHOT_ID"
        python scripts/backup_cli.py restore "$SNAPSHOT_ID" --dry-run
        ;;
    restore)
        if [ -z "$SNAPSHOT_ID" ]; then
            echo "❌ Error: Please specify a snapshot ID to restore."
            print_usage
            exit 1
        fi
        echo "⚠️  Restoring database from snapshot: $SNAPSHOT_ID"
        python scripts/backup_cli.py restore "$SNAPSHOT_ID"
        ;;
    *)
        echo "❌ Unknown command: $COMMAND"
        print_usage
        exit 1
        ;;
esac
