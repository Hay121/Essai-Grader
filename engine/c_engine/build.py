"""
EssayGrader — C Engine Build Script
=====================================
Compiles the essay_engine.c source into a shared library
(.dll on Windows, .so on Linux, .dylib on macOS).

Usage:
    python build.py
"""

import os
import sys
import platform
import subprocess


def build():
    """Compile the C shared library."""
    src_dir = os.path.dirname(os.path.abspath(__file__))
    src_file = os.path.join(src_dir, 'essay_engine.c')

    system = platform.system()
    if system == 'Windows':
        out_file = os.path.join(src_dir, 'essay_engine.dll')
        cmd = ['gcc', '-O3', '-shared', '-o', out_file, src_file, '-lm']
    elif system == 'Linux':
        out_file = os.path.join(src_dir, 'essay_engine.so')
        cmd = ['gcc', '-O3', '-shared', '-fPIC', '-o', out_file, src_file, '-lm']
    elif system == 'Darwin':
        out_file = os.path.join(src_dir, 'essay_engine.dylib')
        cmd = ['gcc', '-O3', '-shared', '-fPIC', '-o', out_file, src_file, '-lm']
    else:
        print(f"[BUILD] Unsupported platform: {system}")
        sys.exit(1)

    print(f"[BUILD] Compiling {src_file}...")
    print(f"[BUILD] Command: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode == 0:
            size = os.path.getsize(out_file)
            print(f"[BUILD] ✓ Success: {out_file} ({size:,} bytes)")
        else:
            print(f"[BUILD] ✗ Compilation failed:")
            print(result.stderr)
            sys.exit(1)
    except FileNotFoundError:
        print("[BUILD] ✗ gcc not found. Install MinGW (Windows) or gcc (Linux).")
        print("[BUILD]   The system will use NumPy fallback instead.")
        sys.exit(1)


if __name__ == '__main__':
    build()
