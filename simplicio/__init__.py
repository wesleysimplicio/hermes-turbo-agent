"""simplicio — task-to-code 6-layer contract pipeline.

Vendored from the standalone ``simplicio-cli`` project
(https://github.com/wesleysimplicio/simplicio-cli, v0.2.3, MIT) so that the
contract is available in-tree without a network install. The package stays
self-contained and portable: ``numpy`` / ``sentence-transformers`` are imported
lazily inside the functions that need them so the module tree imports cleanly
even when the embedding stack is not installed (it is lazy-installed on demand
via ``tools/lazy_deps.py`` feature ``simplicio.embeddings``).
"""

__version__ = "0.2.3"
