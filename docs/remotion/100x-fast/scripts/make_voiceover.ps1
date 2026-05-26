Add-Type -AssemblyName System.Speech

$soundDir = Resolve-Path (Join-Path $PSScriptRoot "..\public\sound")
$voicePath = Join-Path $soundDir "hermes-100x-fast-voiceover.wav"

$ssml = @'
<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
  <prosody rate="-6%" pitch="+1st">
    Meet Hermes Agent one hundred X fast.
    <break time="850ms"/>
    A measured performance pass for the paths users feel every day: messages, tasks, delegation, and runtime resources.
    <break time="850ms"/>
    Before: repeated metadata probes, row by row session writes, slow local endpoint timeouts, and serial tool waits.
    <break time="850ms"/>
    After: cache first metadata, batched SQLite writes, TCP fast fail, and safe parallel tools.
    <break time="850ms"/>
    The latest local benchmarks show metadata lookups completing in point four two one one seconds for one hundred resets over five hundred models.
    <break time="650ms"/>
    Session writes are thirty seven point seven four times faster.
    <break time="500ms"/>
    Endpoint startup is nine point two five times faster.
    <break time="500ms"/>
    Parallel tools are five point two times faster.
    <break time="500ms"/>
    Startup discovery lands in the two to three X class.
    <break time="850ms"/>
    The playbook is documented so the next Hermes release can reapply these changes one optimization at a time.
    <break time="850ms"/>
    The result is simple: fewer wasted waits, more useful work, and a branch ready to benchmark again when Hermes moves forward.
    <break time="800ms"/>
    Hermes Agent one hundred X fast.
    <break time="450ms"/>
    Built for speed, measured for trust, and ready to share.
  </prosody>
</speak>
'@

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$synth.Rate = 0
$synth.Volume = 100
$synth.SetOutputToWaveFile($voicePath)
$synth.SpeakSsml($ssml)
$synth.Dispose()

Get-Item $voicePath
