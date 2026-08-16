"""
memorymate.py — MemoryMate unified entry point
==============================================

One command to launch any surface of MemoryMate. Everything is local:
patient data, camera events, and caregiver logs stay on this device.

    python memorymate.py                web app (patient pages + caregiver console)
    python memorymate.py --web          same as above (default)
    python memorymate.py --camera       camera/gesture interface (GRID/AIR/ASL/FACE/ASSIST/MEMO)
    python memorymate.py --demo         camera-free synthetic-hand tour + caregiver dashboard
                                        (seeds clearly-labelled demo events so the whole
                                         loop is visible in under 2 minutes)

All surfaces share one storage layer (memory/): objects, recalls, gesture
alerts, safety events, routines, and the activity log. The camera app is a
client of that shared core, not a parallel app.
"""

import argparse
import sys
import threading
import time
import urllib.request


def _start_web(host: str = "127.0.0.1", port: int = 5000) -> None:
    """Run the Flask app (patient pages + caregiver console)."""
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    from memory_mate import create_app
    mate = create_app()
    print("MemoryMate web app starting...")
    print(f"  Patient app  : http://localhost:{port}")
    print(f"  Caregiver    : http://localhost:{port}/caregiver")
    mate.app.run(host=host, port=port, debug=False, use_reloader=False)


def _wait_for(url: str, timeout: float = 15.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.3)
    return False


def _run_demo(seed: bool = True) -> None:
    """Demo mode: seed a visible end-to-end story, start the caregiver
    dashboard, then run the camera-free synthetic-hand tour alongside it."""
    if seed:
        try:
            from memory.alerts import seed_demo_events
            seed_demo_events()
            print("Seeded DEMO events: object taught, HELP gesture, safety event (labelled 'demo').")
        except Exception as e:
            print(f"Demo seeding skipped: {e}")

    thread = threading.Thread(target=_start_web, daemon=True)
    thread.start()

    if _wait_for("http://127.0.0.1:5000/"):
        print("Caregiver dashboard is live — open http://localhost:5000/caregiver")
        print("Watch DEMO events appear there while the synthetic hand runs the tour.\n")
    else:
        print("Could not reach the web dashboard (port 5000 busy?).")
        print("Running the camera tour anyway — open the dashboard yourself.\n")

    import index
    index.main(["--demo"])


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="MemoryMate — assistive communication & memory system (single entry point)")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--web", action="store_true",
                       help="web app: patient pages + caregiver console (default)")
    group.add_argument("--camera", action="store_true",
                       help="camera/gesture interface (GRID/AIR/ASL/FACE/ASSIST/MEMO)")
    group.add_argument("--demo", action="store_true",
                       help="camera-free demo tour + caregiver dashboard, no setup needed")
    parser.add_argument("--no-seed", action="store_true",
                        help="with --demo: skip seeding labelled demo events")
    parser.add_argument("--port", type=int, default=5000,
                        help="web port (default: 5000)")
    parser.add_argument("--real-keys", action="store_true",
                        help="with --demo: send real keystrokes (default: on-screen only)")
    args = parser.parse_args(argv)

    if args.demo:
        _run_demo(seed=not args.no_seed)
    elif args.camera:
        import index
        index.main([])  # webcam 0; pass --real-keys through as needed
    else:
        _start_web(port=args.port)


if __name__ == "__main__":
    main()
