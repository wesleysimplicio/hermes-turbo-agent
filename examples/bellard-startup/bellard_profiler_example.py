#!/usr/bin/env python3
"""
Example: Bellard-Inspired Minimal Startup Profiler

Demonstrates how to apply Bellard's minimalism principles to Hermes Turbo Agent startup.
This is NOT production code — it's an illustrative example showing the approach.

Key concepts demonstrated:
1. Lazy imports (defer heavy module loads)
2. Pre-compiled manifest (skip directory scan)
3. Minimal cold path (version/help in <100ms)
"""

import time
import importlib
import json
import sys
import os
from pathlib import Path
from typing import Dict, List, Optional


# =============================================================================
# Example 1: Pre-compiled Manifest (inspired by TCCBOOT manifest approach)
# =============================================================================
MANIFEST_CACHE = Path.home() / ".hermes-turbo" / "manifest_cache.json"

def build_manifest(agent_root: Path) -> Dict:
    """Build a pre-compiled manifest of all tools, skills, and plugins.
    
    Instead of scanning directories every boot (slow os.walk), 
    cache the structure once and re-read it as JSON.
    This is the core Bellard insight: put discovery cost at install time.
    """
    manifest = {
        "version": 1,
        "built_at": time.time(),
        "tools": [],
        "skills": [],
        "plugins": [],
        "gateways": [],
    }
    
    # Scan tool directories
    tools_dir = agent_root / "tools"
    if tools_dir.exists():
        for f in sorted(tools_dir.iterdir()):
            if f.suffix == ".py" and f.stem != "__init__":
                manifest["tools"].append(f.stem)
    
    # Scan skill directories
    skills_dir = agent_root / "skills"
    if skills_dir.exists():
        for d in sorted(skills_dir.iterdir()):
            if d.is_dir() and not d.name.startswith("_"):
                manifest["skills"].append(d.name)
    
    return manifest


def get_manifest(agent_root: Path) -> Dict:
    """Get manifest, using cache if fresh."""
    if MANIFEST_CACHE.exists():
        cached = json.loads(MANIFEST_CACHE.read_text())
        # Cache valid for 1 hour — another Bellard lesson: don't re-discover
        if time.time() - cached.get("built_at", 0) < 3600:
            return cached
    
    manifest = build_manifest(agent_root)
    MANIFEST_CACHE.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_CACHE.write_text(json.dumps(manifest, indent=2))
    return manifest


# =============================================================================
# Example 2: Lazy Module Loader (inspired by QuickJS minimal init)
# =============================================================================
class LazyLoader:
    """Defer module import until first use.
    
    Hermes imports ~26 top-level modules on startup, most unused for --version.
    QuickJS starts in <300µs because it doesn't load what it doesn't need.
    """
    
    def __init__(self):
        self._loaded: Dict[str, object] = {}
        self._pending: Dict[str, str] = {}
    
    def register(self, name: str, module_path: str):
        """Register a module to be lazy-loaded."""
        self._pending[name] = module_path
    
    def __getattr__(self, name: str):
        if name in self._pending:
            if name not in self._loaded:
                module_path = self._pending.pop(name)
                self._loaded[name] = importlib.import_module(module_path)
            return self._loaded[name]
        raise AttributeError(f"Module '{name}' not registered")
    
    def prewarm(self, names: List[str]):
        """Pre-warm specific modules (for daemon mode)."""
        for name in names:
            getattr(self, name)  # triggers load


# =============================================================================
# Example 3: Minimal Bare-Metal Path (TCCBOOT-style)
# =============================================================================
class MinimalAgent:
    """Agent with zero import overhead for simple commands.
    
    Inspired by TCCBOOT which compiles a full Linux kernel 
    — we keep a minimal "kernel" that can respond to --version, --help
    without loading the full agent machinery.
    """
    
    def __init__(self):
        # These are the ONLY imports for version/help — everything else is lazy
        self._startup_time = time.time()
        self._manifest: Optional[Dict] = None
        self._version = "0.0.0"  # Would read from actual package version
    
    @property
    def manifest(self) -> Dict:
        if self._manifest is None:
            agent_root = Path(__file__).parent.parent
            t0 = time.perf_counter()
            self._manifest = get_manifest(agent_root)
            elapsed = time.perf_counter() - t0
            if elapsed > 0.01:
                print(f"[warn] Manifest load took {elapsed*1000:.1f}ms — consider pre-build")
        return self._manifest
    
    def version(self) -> str:
        """Respond in <100ms — the Bellard target."""
        return f"Hermes Turbo Agent v{self._version}  (startup: {time.time() - self._startup_time:.3f}s)"
    
    def list_tools(self) -> List[str]:
        """Use manifest instead of scanning directories."""
        return self.manifest.get("tools", [])


# =============================================================================
# Example 4: Daemon Warm Resilience
# =============================================================================
class WarmDaemon:
    """Keep core resident; re-init per-session.
    
    Bellard's TCCBOOT loads a kernel once and keeps it hot.
    Same idea: pre-warm the Python runtime, reset session state on reconnect.
    """
    
    def __init__(self):
        self._core = MinimalAgent()
        self._session_count = 0
        self._ready = True
    
    def new_session(self) -> MinimalAgent:
        """Return a session agent with pre-warmed core.
        
        Per-session state is lightweight; the heavy imports stay in the parent process.
        """
        self._session_count += 1
        # Copy-on-write semantics: session agent shares core, overrides only session data
        return self._core


# =============================================================================
# Benchmark helpers
# =============================================================================
def measure_startup(iterations: int = 100) -> Dict:
    """Measure cold-start time using hyperfine-like logic."""
    times = []
    for _ in range(iterations):
        t0 = time.perf_counter()
        agent = MinimalAgent()
        _ = agent.version()
        times.append(time.perf_counter() - t0)
    
    times.sort()
    return {
        "min": times[0],
        "p50": times[len(times) // 2],
        "p95": times[int(len(times) * 0.95)],
        "max": times[-1],
        "mean": sum(times) / len(times),
        "n": iterations,
    }


if __name__ == "__main__":
    print("=== Bellard Startup Profiler Example ===")
    print()
    
    # Demo: Minimal agent startup
    print("1. MinimalAgent startup:")
    t0 = time.perf_counter()
    agent = MinimalAgent()
    ver = agent.version()
    startup = time.perf_counter() - t0
    print(f"   {ver}")
    print(f"   Startup: {startup*1000:.1f}ms")
    print()
    
    print("2. Manifest (pre-compiled cache):")
    t0 = time.perf_counter()
    tools = agent.list_tools()
    elapsed = time.perf_counter() - t0
    print(f"   Tools found: {len(tools)}")
    print(f"   Manifest load: {elapsed*1000:.1f}ms")
    print()
    
    print("3. Warm daemon (re-use core):")
    daemon = WarmDaemon()
    t0 = time.perf_counter()
    s1 = daemon.new_session()
    _ = s1.version()
    elapsed1 = time.perf_counter() - t0
    
    t0 = time.perf_counter()
    s2 = daemon.new_session()
    _ = s2.version()
    elapsed2 = time.perf_counter() - t0
    
    print(f"   First session: {elapsed1*1000:.1f}ms")
    print(f"   Second session: {elapsed2*1000:.1f}ms  (warm)")
    print()
    
    print("4. Benchmark (10 iterations):")
    results = measure_startup(10)
    print(f"   Min:    {results['min']*1000:.1f}ms")
    print(f"   P50:    {results['p50']*1000:.1f}ms")
    print(f"   P95:    {results['p95']*1000:.1f}ms")
    print(f"   Mean:   {results['mean']*1000:.1f}ms")
