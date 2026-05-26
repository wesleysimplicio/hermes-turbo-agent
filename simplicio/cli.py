"""cli.py — commands: index (cache repo), task (run pipeline), bench, smoke."""
import argparse
from .precedent import index_repo
from .pipeline import run
from .bench import run_bench
from .providers import generate, info

def main():
    ap = argparse.ArgumentParser(prog="simplicio")
    sub = ap.add_subparsers(dest="cmd", required=True)

    pi = sub.add_parser("index", help="index/cache the repo (once, or after changes)")
    pi.add_argument("--root", default="."); pi.add_argument("--stack", default="angular")

    pt = sub.add_parser("task", help="run a task")
    pt.add_argument("goal")
    pt.add_argument("--root", default="."); pt.add_argument("--stack", default="angular")
    pt.add_argument("--target", required=True)
    pt.add_argument("--criteria", default="- true state\n- false state")
    pt.add_argument("--constraints", default="- build passes")


    pb = sub.add_parser("bench", help="compare with vs without (real numbers)")
    pb.add_argument("--root", default="."); pb.add_argument("--stack", default="angular")
    pb.add_argument("--cases", default="bench/cases.json")


    sub.add_parser("smoke", help="one proof call: connect+generate (needs SIMPLICIO_MODEL+KEY)")

    a = ap.parse_args()
    if a.cmd == "index":
        index_repo(a.root, a.stack)
    elif a.cmd == "smoke":
        print("provider:", info())
        out = generate("Reply exactly: OK simplicio connected.")
        print("model reply:", out.strip()[:200])
    elif a.cmd == "bench":
        run_bench(a.root, a.stack, a.cases)
    else:
        run(a.root, a.stack, a.goal, a.target, a.criteria, a.constraints)

if __name__ == "__main__":
    main()
