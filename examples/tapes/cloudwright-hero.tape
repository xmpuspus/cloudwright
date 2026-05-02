# Cloudwright hero demo
# Compile with: vhs examples/tapes/cloudwright-hero.tape

Output examples/cloudwright-hero.gif

Set Shell "bash"
Set FontSize 16
Set Width 1100
Set Height 620
Set Theme "Catppuccin Mocha"
Set TypingSpeed 35ms
Set PlaybackSpeed 1.0
Set Padding 20

# Activate the worktree venv so VHS picks up the local CLI
Hide
Type "cd /Users/xavier/Desktop/cloudwright/.claude/worktrees/v1.3-audit-fixes" Enter
Type "source .venv/bin/activate" Enter
Type "rm -rf demo && mkdir demo && cd demo" Enter
Type "clear" Enter
Show

Sleep 500ms
Type "cloudwright init -t three_tier_web --name healthcare-api --compliance hipaa,soc2 -o spec.yaml"
Sleep 600ms
Enter
Sleep 2.5s

Type "cloudwright cost spec.yaml --workload-profile medium"
Sleep 500ms
Enter
Sleep 3s

Type "cloudwright validate spec.yaml --compliance hipaa,soc2"
Sleep 500ms
Enter
Sleep 3s

Type "cloudwright export spec.yaml --format terraform -o ./infra"
Sleep 500ms
Enter
Sleep 2.5s

Type "cloudwright export spec.yaml --format pulumi-ts -o ./pulumi-infra"
Sleep 500ms
Enter
Sleep 2.5s

Type "ls infra/ pulumi-infra/"
Sleep 500ms
Enter
Sleep 2.5s
