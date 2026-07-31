# Cloudwright offline-review demo: `cloudwright review` + control traceability
# Render from the repo root: vhs examples/tapes/cloudwright-review.tape
# It runs the main checkout's .venv against examples/patient-portal.yaml.
# Both commands unset the API keys first, because neither needs one.

Output examples/cloudwright-review-demo.gif

Set Shell "bash"
Set FontSize 13
Set Width 1000
Set Height 720
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 16ms

Hide
Type "cd /Users/xavier/Desktop/cloudwright && source .venv/bin/activate" Enter
Type "unset ANTHROPIC_API_KEY OPENAI_API_KEY" Enter
Type "clear" Enter
Show

Sleep 500ms
Type "# Scorer, linter and validator in one report. No API key, no network."
Enter
Sleep 600ms
Type "cloudwright review examples/patient-portal.yaml --compliance hipaa"
Sleep 300ms
Enter
Sleep 6.5s

Hide
Type "clear" Enter
Sleep 300ms
Show

Type "# The chain an auditor asks for: component, resource, control, status"
Enter
Sleep 600ms
Type "cloudwright compliance examples/patient-portal.yaml -f hipaa --no-checkov --traceability"
Sleep 300ms
Enter
Sleep 6.5s
