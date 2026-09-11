# What the numbers were measured on.
#
# Microseconds mean nothing without it: this benchmark allocates and walks
# small objects, so it reads the memory subsystem more than the clock, and
# the same code lands differently on a laptop and on a server whose cores
# are shared with something else. Everything here is read from the machine
# itself, and whatever cannot be read is left out rather than guessed.
import os
import platform
import re
import subprocess


def _first(path, pattern):
    """The first capture of `pattern` in `path`, or None if neither is there."""
    try:
        with open(path) as handle:
            match = re.search(pattern, handle.read(), re.MULTILINE)
    except OSError:
        return None
    return match.group(1).strip() if match else None


def _cpu():
    name = _first("/proc/cpuinfo", r"^model name\s*:\s*(.+)$") or platform.processor()
    if not name:
        return None
    cores = _first("/proc/cpuinfo", r"^cpu cores\s*:\s*(\d+)$")
    threads = os.cpu_count()
    if cores and threads:
        return "%s, %s cores / %d threads" % (name, cores, threads)
    return "%s, %d threads" % (name, threads) if threads else name


def _governor():
    """How the kernel is allowed to move the clock, which decides repeatability."""
    return _first("/sys/devices/system/cpu/cpu0/cpufreq/scaling_governor", r"^(\S+)$")


def _memory():
    total = _first("/proc/meminfo", r"^MemTotal:\s+(\d+) kB$")
    size = "%.0f GiB" % (int(total) / 1024 / 1024) if total else None
    # The speed of the DIMMs is what this benchmark actually reads, and only
    # root is allowed to ask -- so whoever runs it can say instead, and on a
    # machine where nobody can, the size is still worth having.
    speed = os.environ.get("BENCH_MEMORY_SPEED")
    if speed:
        return "%s at %s" % (size, speed) if size else speed
    try:
        out = subprocess.run(
            ["dmidecode", "-t", "memory"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if out.returncode == 0:
            speeds = set(
                re.findall(r"^\s*Configured Memory Speed: (\d+ MT/s)", out.stdout, re.M)
            )
            if len(speeds) == 1:
                speed = speeds.pop()
    except (OSError, subprocess.SubprocessError):
        pass
    if size and speed:
        return "%s at %s" % (size, speed)
    return size


def load_average():
    """What else the machine was doing when the first round started."""
    try:
        one, five, fifteen = os.getloadavg()
    except OSError:
        return None
    return "%.2f, %.2f, %.2f" % (one, five, fifteen)


def describe(postgres=None, load=None):
    """One line per fact worth knowing, as a markdown list.

    `load` is read before the first round by whoever calls this, because
    by the time there is a report to write the benchmark is the load.
    """
    facts = [
        ("CPU", _cpu()),
        ("Frequency governor", _governor()),
        ("Memory", _memory()),
        ("Kernel", "%s %s" % (platform.system(), platform.release())),
        ("PostgreSQL", postgres),
        ("Load average before the first round", load),
    ]
    return "\n".join("- **%s**: %s" % (name, value) for name, value in facts if value)
