#!/usr/bin/env python3
"""
Direct Computer Use Task Runner
Runs tasks WITHOUT the Streamlit web interface
No timeouts, no disconnects - just pure execution
"""

import asyncio
import sys
import os

# This will run INSIDE the Docker container
# It imports the actual Computer Use loop

async def run_task(task_prompt: str):
    """Run a task using the actual Computer Use loop"""

    # Import from the container's computer_use_demo module
    sys.path.insert(0, '/home/computeruse')
    from computer_use_demo.loop import sampling_loop, APIProvider, ToolVersion
    from anthropic.types.beta import BetaMessageParam

    print("🚀 ARYAN-CLAW DIRECT TASK EXECUTION")
    print("="*80)

    # Show task preview
    task_lines = task_prompt.strip().split('\n')
    if len(task_lines) == 1:
        print(f"📋 Task: {task_prompt[:200]}..." if len(task_prompt) > 200 else f"📋 Task: {task_prompt}")
    else:
        print(f"📋 Task ({len(task_lines)} lines):")
        for i, line in enumerate(task_lines[:5], 1):
            preview = line[:75] + "..." if len(line) > 75 else line
            print(f"   {i}. {preview}")
        if len(task_lines) > 5:
            print(f"   ... ({len(task_lines) - 5} more lines)")

    print("\n" + "="*80)
    print("🔄 EXECUTION STARTED")
    print("="*80 + "\n")

    messages = [
        {
            "role": "user",
            "content": task_prompt
        }
    ]

    def output_callback(content_block):
        """Called for each content block"""
        if isinstance(content_block, dict):
            if content_block.get("type") == "text":
                text = content_block.get('text', '')
                # Print in a more readable format
                if text.strip():
                    print(f"\n💭 Claude: {text}")
            elif content_block.get("type") == "tool_use":
                tool_name = content_block.get('name', '')
                tool_input = content_block.get('input', {})

                # Make tool usage more readable
                if tool_name == "computer":
                    action = tool_input.get('action', '')
                    if action == "screenshot":
                        print(f"\n📸 Taking screenshot...")
                    elif action == "mouse_move":
                        print(f"\n🖱️  Moving mouse...")
                    elif action == "left_click":
                        print(f"\n👆 Clicking...")
                    elif action == "type":
                        text_preview = tool_input.get('text', '')[:50]
                        print(f"\n⌨️  Typing: {text_preview}...")
                    elif action == "key":
                        key = tool_input.get('text', '')
                        print(f"\n⌨️  Pressing key: {key}")
                    else:
                        print(f"\n🔧 Computer action: {action}")
                elif tool_name == "bash":
                    command = tool_input.get('command', '')[:60]
                    print(f"\n💻 Running command: {command}...")
                else:
                    print(f"\n🔧 Using tool: {tool_name}")

    def tool_output_callback(result, tool_use_id):
        """Called after tool execution"""
        if result.output:
            # Show abbreviated success for computer actions
            if "screenshot" in str(result.output).lower():
                print(f"   ✓ Screenshot captured")
            elif len(result.output) < 200:
                print(f"   ✓ {result.output}")
            else:
                # Truncate long outputs
                preview = result.output[:100].replace('\n', ' ')
                print(f"   ✓ Output: {preview}...")
        if result.error:
            print(f"   ✗ Error: {result.error}")

    def api_response_callback(request, response, error):
        """Called for each API call"""
        if error:
            print(f"\n❌ API Error: {error}")
        else:
            # Show API call number
            import time
            timestamp = time.strftime("%H:%M:%S")
            print(f"\n⚡ API call at {timestamp}")

    # Get API key from environment
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not found in environment")
        return

    try:
        # Run the actual sampling loop
        # This is the EXACT same loop the Streamlit app uses
        # But without any web interface to disconnect!
        final_messages = await sampling_loop(
            model="claude-sonnet-4-5-20250929",
            provider=APIProvider.ANTHROPIC,
            system_prompt_suffix="",
            messages=messages,
            output_callback=output_callback,
            tool_output_callback=tool_output_callback,
            api_response_callback=api_response_callback,
            api_key=api_key,
            only_n_most_recent_images=10,
            max_tokens=4096,
            tool_version="computer_use_20250124",
            thinking_budget=None,
            token_efficient_tools_beta=False
        )

        print("\n" + "="*80)
        print("✅ TASK COMPLETED SUCCESSFULLY!")
        print("="*80)
        print(f"\n📊 Stats:")
        print(f"   • Total message exchanges: {len(final_messages)}")
        print(f"   • Task duration: Complete")
        print(f"\n💡 Tip: Check http://localhost:6080 to see the final desktop state")
        print("")

    except Exception as e:
        print("\n" + "="*80)
        print("❌ TASK FAILED WITH ERROR")
        print("="*80)
        print(f"\n⚠️  Error: {e}")
        print("")
        import traceback
        print("Stack trace:")
        traceback.print_exc()
        print("")
        print("💡 Tip: Check if the Computer Use container is running:")
        print("   docker ps | grep aryan-claw-local")
        print("")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 direct_task_runner.py <task_file>")
        print("Or pipe task via stdin")
        sys.exit(1)

    if sys.argv[1] == "-":
        # Read from stdin
        task = sys.stdin.read()
    else:
        # Read from file
        with open(sys.argv[1], 'r') as f:
            task = f.read()

    asyncio.run(run_task(task))
