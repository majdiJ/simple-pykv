import time
import sys
import os
from typing import Iterable, Set, Tuple
from classes.config import Config

def get_process_memory_bytes():
    # Try psutil (cross-platform, best)
    try:
        import psutil
        proc = psutil.Process()
        # .rss is resident set size in bytes
        memory_bytes = proc.memory_info().rss
        return memory_bytes
    except Exception:
        pass

    # Try resource (Unix). Note: ru_maxrss units differ by platform.
    try:
        import resource
        ru = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        # On Linux, ru_maxrss is in kilobytes; on macOS/BSD it's bytes.
        if sys.platform.startswith("linux"):
            return int(ru) * 1024
        else:
            # macOS / BSD usually return bytes
            return int(ru)
    except Exception:
        pass

    # Fallback for Linux: parse /proc/self/status (VmRSS)
    try:
        if sys.platform.startswith("linux"):
            with open("/proc/self/status", "r") as f:
                for line in f:
                    if line.startswith("VmRSS:"):
                        parts = line.split()
                        # e.g. "VmRSS:    123456 kB"
                        value_kb = int(parts[1])
                        return value_kb * 1024
    except Exception:
        pass

    # Last resort: unknown platform/no method -> return 0 or raise
    raise RuntimeError("Unable to determine process memory usage on this platform.")

def get_folder_size_bytes(path: str, *, follow_symlinks: bool = False, count_hardlinks_once: bool = True, use_allocated_blocks_if_available: bool = False) -> int:
    total = 0
    # To avoid double counting files with multiple hard links
    seen_inodes: Set[Tuple[int, int]] = set()

    # To avoid directory cycles when following symlinks: track visited directories by (st_dev, st_ino)
    seen_dirs: Set[Tuple[int, int]] = set()

    # Normalise starting path and seed stack
    try:
        start_stat = os.stat(path, follow_symlinks=follow_symlinks)
    except FileNotFoundError:
        return 0
    except PermissionError:
        return 0

    stack = [os.path.abspath(path)]

    while stack:
        current = stack.pop()
        try:
            with os.scandir(current) as it:
                for entry in it:
                    try:
                        # Get stat for files; follow_symlinks parameter controls behavior
                        st = entry.stat(follow_symlinks=follow_symlinks)
                    except FileNotFoundError:
                        # file was removed between listing and stat
                        continue
                    except PermissionError:
                        # can't stat this entry; skip it
                        continue
                    # If it's a directory, push to stack (respecting follow_symlinks)
                    if entry.is_dir(follow_symlinks=follow_symlinks):
                        dir_id = (getattr(st, "st_dev", 0), getattr(st, "st_ino", 0))
                        if dir_id in seen_dirs:
                            # already visited (prevents cycles if following symlinks)
                            continue
                        seen_dirs.add(dir_id)
                        # push path (if symlink and follow_symlinks False, is_dir() above is False)
                        try:
                            stack.append(entry.path)
                        except Exception:
                            # fallback: build full path
                            stack.append(os.path.join(current, entry.name))
                    elif entry.is_file(follow_symlinks=follow_symlinks) or entry.is_symlink():
                        # handle files and symlinks-to-files
                        file_id = (getattr(st, "st_dev", 0), getattr(st, "st_ino", 0))
                        if count_hardlinks_once and file_id in seen_inodes:
                            continue
                        seen_inodes.add(file_id)

                        if use_allocated_blocks_if_available and hasattr(st, "st_blocks"):
                            # st_blocks is number of 512-byte blocks on POSIX systems
                            total += int(st.st_blocks) * 512
                        else:
                            total += int(st.st_size)
                    else:
                        # other types (fifo, socket, etc.) — ignore or handle as you wish
                        continue
        except PermissionError:
            # can't open this directory; skip
            continue
        except FileNotFoundError:
            # dir removed after we queued it; skip
            continue
        except NotADirectoryError:
            # In case the path we pushed isn't a directory anymore — skip
            continue

    return total

class system_info:

    def __init__(self, config_instance: Config):
        # system information module
        self.simple_pykv_version = "0.0.0 (Beta)"
        self.start_time = time.time()
        self.config_instance = config_instance
    
    def get_system_info(self):
        updated_info = {
            "version": self.simple_pykv_version,
            "uptime": int(time.time() - self.start_time),
            "memory_usage_bytes": get_process_memory_bytes(),
            "storage_usage_bytes": get_folder_size_bytes(self.config_instance.get_config_data().get("system", {}).get("storage", {}).get("persistent_file_path", "storage_data")),
            "number_of_projects": self.config_instance.get_number_of_projects()
        }
        return updated_info

