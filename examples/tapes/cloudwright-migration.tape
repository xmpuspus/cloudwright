# Cloudwright migration planning and evidence demo
# Run from the repository root: vhs examples/tapes/cloudwright-migration.tape
# The project and evidence files are local, and both commands run without API keys.

Output examples/cloudwright-migration-cli-demo.gif

Set Shell "bash"
Set FontSize 13
Set Width 1100
Set Height 720
Set Padding 18
Set Theme "Catppuccin Mocha"
Set TypingSpeed 14ms

Hide
Type 'cd "$(git rev-parse --show-toplevel)"' Enter
Type "unset ANTHROPIC_API_KEY OPENAI_API_KEY" Enter
Type 'mkdir -p "$PWD/tmp"' Enter
Type 'migration_demo_dir=$(mktemp -d "$PWD/tmp/migration-gif.XXXXXX")' Enter
Type "clear" Enter
Show

Sleep 600ms
Type "# Source estate and target become dependency-ordered waves with explicit costs"
Enter
Sleep 600ms
Type 'python3 -m cloudwright_cli migrate plan examples/migrations/ph-telco-project.yaml -o "$migration_demo_dir/assessment.yaml"'
Sleep 300ms
Enter
Sleep 5s

Hide
Type "clear" Enter
Sleep 300ms
Show

Type "# Recorded evidence decides whether the migration can close"
Enter
Sleep 600ms
Type 'python3 -m cloudwright_cli migrate verify "$migration_demo_dir/assessment.yaml" examples/migrations/ph-telco-evidence.yaml'
Sleep 300ms
Enter
Sleep 4s
