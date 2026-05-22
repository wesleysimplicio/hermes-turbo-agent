# Hermes Turbo Agent Variants

`Hermes Turbo Agent` now ships two ready-to-install profile distributions in
this repository.

## Desktop

Path: `distributions/hermes-turbo-desktop/`

Use this when the operator is running on a laptop or workstation and needs:

- coding and repository work
- browser and desktop automation
- release, validation, and operator dashboards
- long autonomous `/goal` style execution loops

Install:

```bash
hermes profile install ./distributions/hermes-turbo-desktop --name hermes-turbo-desktop --alias
```

## Car

Path: `distributions/hermes-turbo-car/`

Use this when the operator needs an in-car or moving-operator copilot flow:

- voice-first summaries
- task capture from meetings, calls, and quick notes
- route-safe planning and reminder handoff
- hands-free status and next-step coordination

Install:

```bash
hermes profile install ./distributions/hermes-turbo-car --name hermes-turbo-car --alias
```

## Compatibility

- Prefer the new installed commands: `hermes-turbo`, `hermes-turbo-agent`, and
  `hermes-turbo-acp`.
- The runtime still accepts `TOTA_HOME` and old `tota*` commands.
- `HERMES_TURBO_HOME` is the new preferred home override.
- The default storage directory remains `~/.tota` for backward compatibility.
