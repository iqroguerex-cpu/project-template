import json
import os
import sys
from openai import OpenAI

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("❌ Error: OPENROUTER_API_KEY environment variable is missing.")
    sys.exit(1)

MODEL_NAME = "nvidia/nemotron-3-ultra-550b-a55b:free"

def scan_directory_tree(target_dir: str = ".") -> str:
    """Builds an ASCII file tree of the project up to 3 levels deep."""
    ignore_list = {".git", ".github", "__pycache__", "node_modules", "venv", ".env"}
    tree_lines = [f"{os.path.basename(os.path.abspath(target_dir))}/"]
    
    for root, dirs, files in os.walk(target_dir):
        dirs[:] = [d for d in dirs if d not in ignore_list]
        level = root.replace(target_dir, '').count(os.sep)
        if level > 3:
            continue
        indent = "│   " * level
        sub_indent = "├── "
        for f in sorted(files):
            if not f.startswith(".") and f != "README.md":
                tree_lines.append(f"{indent}{sub_indent}{f}")
                
    return "\n".join(tree_lines[:70])

def read_code_files(filepaths_json: str) -> str:
    """Reads the contents of core entry points, requirements, or configs."""
    try:
        paths = json.loads(filepaths_json)
        results = {}
        for path in paths:
            if os.path.exists(path) and os.path.isfile(path):
                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    results[path] = f.read(3000)
            else:
                results[path] = "File not found."
        return json.dumps(results, indent=2)
    except Exception as e:
        return f"Error reading files: {str(e)}"

def save_readme(content: str, filename: str = "README.md") -> str:
    """Saves the generated markdown to disk."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(content)
        return f"SUCCESS: Saved {filename}"
    except Exception as e:
        return f"ERROR: {str(e)}"

AVAILABLE_TOOLS = {
    "scan_directory_tree": scan_directory_tree,
    "read_code_files": read_code_files,
    "save_readme": save_readme
}

tool_schemas = [
    {
        "type": "function",
        "function": {
            "name": "scan_directory_tree",
            "description": "Scans the project tree of files and directories.",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_code_files",
            "description": "Reads source files, manifests, and configs. Pass JSON list of relative paths.",
            "parameters": {
                "type": "object",
                "properties": {
                    "filepaths_json": {"type": "string", "description": "e.g. '[\"app.py\", \"requirements.txt\"]'"}
                },
                "required": ["filepaths_json"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_readme",
            "description": "Saves the complete markdown text to README.md.",
            "parameters": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Full Markdown content"}
                },
                "required": ["content"]
            }
        }
    }
]

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
    default_headers={
        "HTTP-Referer": "https://github.com",
        "X-Title": "Auto-README-Agent"
    }
)

SYSTEM_PROMPT = """
You are an autonomous Documentation Engineer. Analyze the repository files and generate/update the project's README.md.

MANDATORY RULES:
1. AUTHOR: The Author section must STRICTLY state:
   ## 👨‍💻 Author
   **Chinmay V Chatradamath**
   (Do NOT add any other names, co-authors, or placeholders).

2. TEMPLATE STRUCTURE:
   # 📊 <PROJECT_NAME> | <TAGLINE>
   <p align="center">
   [Shields.io badges: Language, Framework, Libraries, License MIT, Live Demo/Deploy]
   </p>
   ---
   ## 🚀 Overview (Elevated, architectural language explaining the exact problem it solves)
   ## ✨ Features (Bulleted with clean emojis: 🤖, 🎛️, 📊, ⭐, 📈, 🔍, 🎨)
   ## 🛠️ Tech Stack (List verified frameworks and libraries)
   ## 📂 Project Structure (Exact ASCII bash tree)
   ## ⚙️ Installation
   ## ▶️ Run Locally (Exact run command based on inspected files)
   ## 📊 Core Architecture / Model Details (Algorithms, models, endpoints)
   ## 🧠 How It Works (Numbered step-by-step pipeline)
   ## 🎛️ Controls / API Reference
   ## 🚀 Deployment (Streamlit Cloud, Docker, Vercel, or AWS depending on the code)
   ## 🔮 Future Improvements
   ## 👨‍💻 Author
   **Chinmay V Chatradamath**
   ## ⭐ Support

OPERATIONAL STEPS:
1. Call `scan_directory_tree` to discover all existing files.
2. Call `read_code_files` on key files (e.g., app.py, main.py, requirements.txt, package.json).
3. If README.md already exists, incorporate the updates and new features accurately.
4. Save the completed file using `save_readme`.
"""

def main():
    print("🚀 Starting Autonomous README Analysis...")
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "Analyze all files in the current repository, inspect changes, and write/update the README.md."}
    ]

    for turn in range(6):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tool_schemas,
            tool_choice="auto",
            temperature=0.1
        )

        response_msg = response.choices[0].message
        messages.append(response_msg)

        if not response_msg.tool_calls:
            print("✅ Agent finished analysis.")
            break

        for tool_call in response_msg.tool_calls:
            fn_name = tool_call.function.name
            try:
                parsed_args = json.loads(tool_call.function.arguments)
            except Exception:
                parsed_args = {}

            print(f"⚙️ Running tool: {fn_name}")
            tool_fn = AVAILABLE_TOOLS.get(fn_name)
            tool_output = tool_fn(**parsed_args) if tool_fn else "Error: Unknown function."

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": fn_name,
                "content": str(tool_output)
            })

if __name__ == "__main__":
    main()
