"""Token-optimized external adapters.

Submodules:

- ``github_compact``: slim views over ``gh`` CLI output (issue tracking / PR data).
- ``ci_compact``: failing-stage-only summaries of CI logs.
- ``rtk_bridge``: optional RTK CLI bridge with token-saver backend selection
  (https://github.com/rtk-ai/rtk). See docs/integrations/rtk-bridge.md.
"""

from agent.adapters import ci_compact, github_compact, rtk_bridge

__all__ = ["ci_compact", "github_compact", "rtk_bridge"]
