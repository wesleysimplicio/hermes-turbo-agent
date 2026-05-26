"""pipeline.py — build -> generate -> apply -> test -> fix (loop)."""
import os, subprocess
from .prompt import build_prompt
from .providers import generate

MAX_ATTEMPTS = 3

def _apply_and_test(output, root):
    os.makedirs(os.path.join(root, ".simplicio"), exist_ok=True)
    open(os.path.join(root, ".simplicio/last_output.txt"), "w", encoding="utf-8").write(output)
    # PLUG: extract diff -> git apply; extract test. Here we run the test command.
    cmd = os.environ.get("SIMPLICIO_TEST_CMD", "echo 'configure SIMPLICIO_TEST_CMD'")
    p = subprocess.run(cmd, shell=True, cwd=root, capture_output=True, text=True)
    return p.returncode == 0, (p.stdout + p.stderr)[-2000:]

def run(root, stack, goal, target, criteria, constraints):
    prompt = build_prompt(root, stack, goal, target, criteria, constraints)
    feedback = None
    for t in range(1, MAX_ATTEMPTS + 1):
        print(f"--- attempt {t} (provider={os.environ.get('SIMPLICIO_PROVIDER','claude')}) ---")
        output = generate(prompt, feedback)
        ok, log = _apply_and_test(output, root)
        if ok:
            print("PASSED the contract. DONE.")
            return output
        print("failed:", log[:300]); feedback = log
    print("attempts exhausted — manual review needed.")
    return None
