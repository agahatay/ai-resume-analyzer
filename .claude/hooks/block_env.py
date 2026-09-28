import json, os, sys

data = json.load(sys.stdin)
path = data.get("tool_input", {}).get("file_path", "")
name = os.path.basename(path)

if name == ".env" or (name.startswith(".env.") and not name.endswith(".example")):
    print(f"Engellendi: {name} gizli bilgiler iceriyor, elle duzenle.", file=sys.stderr)
    sys.exit(2)
