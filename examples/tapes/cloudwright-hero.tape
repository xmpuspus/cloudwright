# Cloudwright hero demo
# Render from the repo root: vhs examples/tapes/cloudwright-hero.tape
# vhs resolves Output against your current directory, so the repo root is the only
# cwd that lands the GIF in examples/. The shell inside the tape finds the checkout
# with git, so it names no machine path and no worktree, and it works in any clone.
# The earlier version hardcoded a path into .claude/worktrees/. Pruning that
# worktree made vhs record a broken shell and still exit 0.
# Scratch work goes in tmp/hero-demo, which is gitignored.
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
Type 'cd "$(git rev-parse --show-toplevel)" && source .venv/bin/activate' Enter
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
