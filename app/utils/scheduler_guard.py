"""
Scheduler Guard Utility
Ensures only a single worker process runs background schedulers
in multi-worker environments (e.g., Gunicorn with multiple worker processes).
"""

import os
import sys
import logging
import tempfile
import atexit

logger = logging.getLogger(__name__)

# Keep reference to open lock file descriptor so it is not garbage collected
_LOCK_FD = None

def acquire_scheduler_lock(lock_name: str = "skillbridge_scheduler.lock") -> bool:
    """
    Attempts to acquire an exclusive lock for the scheduler.
    Returns True if this process acquired the lock and should run the scheduler.
    Returns False if another process already holds the lock.
    """
    global _LOCK_FD

    # Explicit environment overrides
    if os.environ.get('DISABLE_SCHEDULER', '').lower() in ('true', '1', 'yes'):
        logger.info("⏸️ Scheduler explicitly disabled via DISABLE_SCHEDULER environment variable.")
        return False

    lock_path = os.path.join(tempfile.gettempdir(), lock_name)

    try:
        if sys.platform != 'win32':
            import fcntl
            _LOCK_FD = open(lock_path, 'w')
            # Try non-blocking exclusive flock
            fcntl.flock(_LOCK_FD, fcntl.LOCK_EX | fcntl.LOCK_NB)
            _LOCK_FD.write(str(os.getpid()))
            _LOCK_FD.flush()
            logger.info(f"🔒 Scheduler lock acquired by worker process PID {os.getpid()} on {lock_path}")
            return True
        else:
            # Windows fallback: PID file with active process check
            if os.path.exists(lock_path):
                try:
                    with open(lock_path, 'r') as f:
                        old_pid = int(f.read().strip())
                    # Check if process is still running
                    import ctypes
                    kernel32 = ctypes.windll.kernel32
                    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
                    h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, old_pid)
                    if h_process != 0:
                        kernel32.CloseHandle(h_process)
                        logger.info(f"🔒 Scheduler lock held by existing worker PID {old_pid}. Skipping scheduler in PID {os.getpid()}.")
                        return False
                except Exception:
                    pass  # Stale lock or unparseable PID, proceed to acquire

            # Write current PID
            with open(lock_path, 'w') as f:
                f.write(str(os.getpid()))

            def cleanup():
                try:
                    if os.path.exists(lock_path):
                        with open(lock_path, 'r') as f:
                            if f.read().strip() == str(os.getpid()):
                                os.remove(lock_path)
                except Exception:
                    pass

            atexit.register(cleanup)
            logger.info(f"🔒 Scheduler lock acquired by process PID {os.getpid()} on {lock_path}")
            return True

    except (BlockingIOError, IOError):
        logger.info(f"🔒 Scheduler lock already held by another worker process. Skipping scheduler in PID {os.getpid()}.")
        return False
    except Exception as e:
        logger.warning(f"⚠️ Failed to evaluate scheduler lock: {e}. Defaulting to skipping duplicate scheduler.")
        return False
