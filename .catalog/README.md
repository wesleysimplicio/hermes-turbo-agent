HAMT catalog of yool capabilities. Built from AGENTS.md by
`scripts/build_hamt_catalog.py`. Do not edit by hand.

Spec: https://github.com/wesleysimplicio/yool-tuple-hamt (v0.2).

Constants per Bagwell (2001):

    BITS_PER_LEVEL = 5
    BRANCH         = 32
    MAX_LEVELS     = 6
    HASH_BITS      = 30
    hash           = blake2b truncated to 30 bits

Build:

    python scripts/build_hamt_catalog.py            # writes .catalog/hamt.json
    python scripts/build_hamt_catalog.py --print-list

`hamt.json` and `receipts/` are build artifacts, gitignored.
