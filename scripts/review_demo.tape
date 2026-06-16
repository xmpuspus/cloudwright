# vhs tape: cloudwright review (offline critique) + OSCAL export
# Render: vhs scripts/review_demo.tape   (from repo root, venv on PATH)

Output examples/cloudwright-review-demo.gif

Set Shell "bash"
Set FontSize 16
Set Width 1180
Set Height 860
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 30ms

Hide
Type "export PATH=$PWD/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin; clear"
Enter
Sleep 700ms
Show

Type "# Offline architecture review — no API key. Scorer + linter + validator, one report."
Enter
Sleep 900ms
Type "cloudwright review examples/patient-portal.yaml --compliance hipaa"
Enter
Sleep 5s

Hide
Type "clear"
Enter
Sleep 400ms
Show

Type "# Same findings, exported as an OSCAL 1.1.2 component-definition for FedRAMP/auditors"
Enter
Sleep 900ms
Type "cloudwright compliance examples/patient-portal.yaml --frameworks hipaa --no-checkov --oscal --fail-on none | head -n 24"
Enter
Sleep 5s
