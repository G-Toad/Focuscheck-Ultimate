# Intervention State Machine

`idle -> requested -> selecting -> action -> verified -> completed`.

Cancellation or exception transitions to `failed`, restores a hidden prompt, clears app intervention state, and does not start a website cooldown. A completed website intervention starts cooldown and consumes `allow_once`.

Tk ownership and overlay/window cleanup remain manual Windows evidence gates.
