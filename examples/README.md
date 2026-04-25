# Examples

8 example modules demonstrating apcore-cli usage.

## Quick Start

```bash
# From the project root
pip install -e .
export APCORE_EXTENSIONS_ROOT=examples/extensions

# Run a module
apcore-cli math.add --a 5 --b 10
# {"sum": 15}

# List all modules
apcore-cli list

# Run all examples at once
bash examples/run_examples.sh
```

## Available Modules

| Module | Description | Example |
|--------|-------------|---------|
| `math.add` | Add two integers | `apcore-cli math.add --a 5 --b 10` |
| `math.multiply` | Multiply two integers | `apcore-cli math.multiply --a 6 --b 7` |
| `text.upper` | Uppercase a string | `apcore-cli text.upper --text hello` |
| `text.reverse` | Reverse a string | `apcore-cli text.reverse --text abcdef` |
| `text.wordcount` | Count words/chars/lines | `apcore-cli text.wordcount --text "hello world"` |
| `sysutil.info` | System information | `apcore-cli sysutil.info` |
| `sysutil.env` | Read an env variable | `apcore-cli sysutil.env --name HOME` |
| `sysutil.disk` | Disk usage stats | `apcore-cli sysutil.disk --path /` |

## Writing Your Own Module

Each module is a directory with two files:

```
extensions/
└── greet/
    └── hello/
        ├── module.json    <- descriptor (schema + metadata)
        └── run.sh         <- execution logic (any language)
```

### Step 1: Create `module.json`

Defines the module's ID, description, input/output schemas, and executable:

```json
{
  "name": "greet.hello",
  "description": "Greet someone by name",
  "tags": ["demo"],
  "executable": "run.sh",
  "input_schema": {
    "type": "object",
    "properties": {
      "name": { "type": "string", "description": "Person to greet" },
      "greeting": { "type": "string", "description": "Greeting word", "default": "Hello" }
    },
    "required": ["name"]
  },
  "output_schema": {
    "type": "object",
    "properties": {
      "message": { "type": "string" }
    }
  }
}
```

### Step 2: Create `run.sh`

Reads JSON from stdin, writes JSON to stdout. Can be written in **any language**:

```bash
#!/usr/bin/env bash
python3 -c "
import json, sys
d = json.load(sys.stdin)
name = d['name']
greeting = d.get('greeting', 'Hello')
print(json.dumps({'message': f'{greeting}, {name}!'}))
"
```

Make it executable:

```bash
chmod +x run.sh
```

### Step 3: Run it

```bash
apcore-cli --extensions-dir ./extensions greet.hello --name World
# {"message": "Hello, World!"}

apcore-cli --extensions-dir ./extensions greet.hello --name Alice --greeting Hi
# {"message": "Hi, Alice!"}

# Auto-generated help from input_schema
apcore-cli --extensions-dir ./extensions greet.hello --help
```

### How It Works

```
apcore-cli greet.hello --name World
    │
    ├── 1. Read module.json → register schema + flags
    ├── 2. Parse --name World → {"name": "World"}
    ├── 3. Validate input against input_schema
    └── 4. Spawn run.sh, pipe JSON stdin → stdout
              │
              └── {"message": "Hello, World!"}
```

The CLI only cares about the JSON stdin/stdout protocol. Your `run.sh` can call Python, Node, Rust binaries, APIs, or anything else.

## STDIN Piping

```bash
# Pipe JSON input directly
echo '{"a": 100, "b": 200}' | apcore-cli math.add --input -
# {"sum": 300}

# CLI flags override STDIN values
echo '{"a": 1, "b": 2}' | apcore-cli math.add --input - --a 999
# {"sum": 1001}

# Chain with other tools
apcore-cli sysutil.info | jq '.hostname'
```
