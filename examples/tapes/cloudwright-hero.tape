# Cloudwright hero demo
# Render from the repo root: vhs examples/tapes/cloudwright-hero.tape
# It runs the main checkout's .venv and works in tmp/hero-demo, which is gitignored.
# Do not point this at a git worktree: pruning one breaks the recording silently.
#
# The tape hides the ~15s terraform init+validate wait so the loop stays short.
# The on-screen comment states that wait, so the GIF does not claim plan is instant.

Output examples/cloudwright-hero.gif

Set Shell "bash"
Set FontSize 16
Set Width 1180
Set Height 520
Set Theme "Catppuccin Mocha"
Set TypingSpeed 16ms
Set PlaybackSpeed 1.0
Set Padding 18

Hide
Type "cd /Users/xavier/Desktop/cloudwright && source .venv/bin/activate" Enter
Type "export TF_PLUGIN_CACHE_DIR=$PWD/tmp/tf-plugin-cache && mkdir -p $TF_PLUGIN_CACHE_DIR" Enter
Type "rm -rf tmp/hero-demo && mkdir -p tmp/hero-demo && cd tmp/hero-demo" Enter
Type "clear" Enter
Show

Sleep 500ms
Type "# A typed architecture spec, from a template or from a prompt"
Enter
Sleep 600ms
Type "cloudwright init -t three_tier_web --name healthcare-api --compliance hipaa,soc2 -o spec.yaml"
Sleep 300ms
Enter
Sleep 2.2s

Hide
Type "clear" Enter
Sleep 300ms
Show

Type "# Per-component cost, with a confidence flag on every line"
Enter
Sleep 600ms
Type "cloudwright cost spec.yaml --workload-profile medium"
Sleep 300ms
Enter
Sleep 3.5s

Hide
Type "clear" Enter
Sleep 300ms
Show

Type "# Every finding carries the framework control it violates, before anything exists"
Enter
Sleep 600ms
Type "cloudwright compliance spec.yaml --frameworks hipaa,soc2 --no-checkov"
Sleep 300ms
Enter
Sleep 4.5s

Hide
Type "clear" Enter
Sleep 300ms
Show

Type "# Terraform out, then terraform validate proves it deploys. Read-only, never applies."
Enter
Sleep 600ms
Type "cloudwright export spec.yaml --format terraform -o ./infra"
Sleep 300ms
Enter
Sleep 1.5s
Type "cloudwright plan spec.yaml --target terraform --no-plan   # terraform init + validate, ~15s"
Sleep 300ms
Enter

# The wait itself is not worth 15s of GIF. Skip the frames, keep the result.
Hide
Sleep 20s
Show
Sleep 3.5s
