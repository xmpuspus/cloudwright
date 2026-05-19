# vhs tape: cloudwright compliance + cloudwright plan
# Render: vhs scripts/controls_demo.tape   (from repo root, venv on PATH)

Output examples/cloudwright-controls-demo.gif

Set Shell "bash"
Set FontSize 17
Set Width 1180
Set Height 760
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 32ms

Hide
Type "export PATH=$PWD/.venv/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin; export TF_PLUGIN_CACHE_DIR=$PWD/tmp/tf-plugin-cache; clear"
Enter
Sleep 800ms
Show

Type "# Every finding mapped to the framework control it violates"
Enter
Sleep 900ms
Type "cloudwright compliance examples/healthcare-app.yaml --frameworks hipaa,fedramp --no-checkov --fail-on none | head -n 22"
Enter
Sleep 5s

Hide
Type "clear"
Enter
Sleep 400ms
Show

Type "# Prove the exported Terraform actually deploys (read-only, no apply)"
Enter
Sleep 900ms
Type "cloudwright plan examples/healthcare-app.yaml --target terraform --no-plan"
Enter
Sleep 6s

Type "# Same checks as POST /api/compliance and /api/plan in the web canvas"
Enter
Sleep 2500ms
