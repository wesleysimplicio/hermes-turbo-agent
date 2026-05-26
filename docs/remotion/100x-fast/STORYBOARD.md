# Hermes Agent 100X Fast Video Storyboard

Rendered asset:

- `docs/assets/100x-fast/video/hermes-100x-fast-launch.mp4`
- 90 seconds, 1920x1080, 30fps, H.264 + AAC
- Poster: `docs/assets/100x-fast/video/hermes-100x-fast-poster.png`
- Soundtrack source: `public/sound/hermes-100x-fast-soundtrack.wav`
- Voiceover source: `public/sound/hermes-100x-fast-voiceover.wav`
- README preview: `docs/assets/100x-fast/video/hermes-100x-fast-launch-preview.gif`

## Intent

Make the performance work feel tangible without overstating it. The video says
"100X Fast" as the performance track, then ties every speed claim to a concrete
hot path: metadata cache, session writes, dead endpoint startup, parallel tools,
and startup discovery.

## Timeline

| Time | Scene | Visual | Audio Cue |
| ---: | --- | --- | --- |
| 0-18s | Opening | GPT-image video cover with title, gain chips, captions, and a slow-to-fast transformation | Narration introduces Hermes Agent 100X Fast over a low synth pulse |
| 16-37s | Before vs after | Generated before/after hero and runtime-stack image side by side with a green sweep | Voice calls out repeated probes, row writes, endpoint waits, and serial tool waits |
| 35-57s | Measured gains | Five metric cards animate in: 0.4211s / 100 lookups, 37.74x, 9.25x, 5.20x, 2-3x | Voice names the measured gains while the music stays ducked underneath |
| 55-75s | Safety architecture | Cache, batch, fast-fail, metadata disk cache, and parallel tools appear as connected nodes | Voice explains fallback paths, refresh hooks, cache paths, and regressions |
| 73-90s | Close | Repeatable-playbook message, progress rail, and final "Hermes Agent 100X Fast" mark | Narration closes with the public-share message, music release tail fades cleanly |

## Exact Claims Used

- Metadata cache: fresh disk cache lookup measured at median 0.4211s for 100
  cold memory resets over 500 models in the benchmark scenario.
- Session writes: row-by-row persistence to one transaction, latest local
  sample around 37.74x.
- Endpoint startup: dead numeric loopback probe fast-fail, around 9.25x for the
  measured scenario.
- Parallel tools: independent I/O-bound batch around 5.20x.
- Startup discovery: measured local improvements in the 2x-3x class.

## Re-render

```powershell
cd docs\remotion\100x-fast
npm install
npm run audio
npm run voiceover
npx tsc --noEmit
npm run still
npm run render
npx remotion render src/index.ts Hermes100xFast ../../assets/100x-fast/video/hermes-100x-fast-launch-preview.gif --codec gif --frames=0-2699 --every-nth-frame=10 --scale=0.35 --muted --number-of-gif-loops=0 --concurrency=2
```

If numbers change, update the Remotion source, voiceover script/text, README
claims, MP4, poster, and GIF preview before publishing again.
