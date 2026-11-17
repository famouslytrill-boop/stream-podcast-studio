param([Parameter(Mandatory=$true)][string]$RequestFile)
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
Add-Type -AssemblyName System.Speech
$request = [IO.File]::ReadAllText($RequestFile, [Text.Encoding]::UTF8) | ConvertFrom-Json
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $available = @($synth.GetInstalledVoices() | Where-Object {$_.Enabled} | ForEach-Object {$_.VoiceInfo.Name})
    if ($available -notcontains [string]$request.voice) { throw 'Selected voice is unavailable.' }
    $synth.SelectVoice([string]$request.voice)
    $synth.Rate = [int]$request.rate
    $synth.Volume = 90
    $format = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo(24000, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
    $synth.SetOutputToWaveFile([string]$request.output, $format)
    # Plain text only: no SSML, scripts, paths or remote content interpreted as speech instructions.
    $synth.Speak([string]$request.text)
    $synth.SetOutputToNull()
} finally { $synth.Dispose() }
