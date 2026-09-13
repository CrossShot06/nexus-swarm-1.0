import docker
import tempfile
import os
import re

from ollama import chat
from ai_brain import AIBrain 
from docker.errors import ContainerError


os.environ["DJANGO_ALLOW_ASYNC_UNSAFE"] = "true" 
from swarm_api.models import MissionLog

class SandboxOrchestrator:

    def __init__(self):
        self.image = "nexus-swarm:latest"
        self.client = docker.from_env()

    def extract_code(self, raw_text):
        match = re.search(r"<code_block>(.*?)</code_block>", raw_text, re.DOTALL)
        if match:
            return match.group(1).strip()
        return raw_text.replace("```cpp", "").replace("```", "").strip()

    def execute_cpp(self, user_prompt, run_args="", callback=None):
        
        def stream_log(msg):
            print(msg) 
            if callback:
                callback(msg)

        manager_prompt = """You are a Senior C++ Software Architect.  

Your job is to analyze the user's request and write a strict, step-by-step technical blueprint for a junior developer. 
Detail the exact logic flow, required functions, and edge cases. 

CRITICAL CONSTRAINTS: 
1. Do NOT write any C++ code. Only write the architecture plan in plain text. 
2. Remind the developer they must use `argv` for dynamic inputs, not `std::cin`.
3. EXPLICITLY dictate that all helper functions, classes, and logic blocks MUST be defined globally, outside and above `int main()`. Warn them strictly against using nested functions or complex lambdas inside main."""

        coder_prompt = """You are an automated C++ backend compilation assistant.  
Your absolute priority is to generate syntactically perfect, highly optimized C++ code. 

CRITICAL RULES: 
1. You MUST place all executable C++ code strictly inside <code_block> and </code_block> tags. 
2. Do NOT use markdown code fences (like ```cpp) inside or outside the tags. 
3. Any explanations, thought processes, or debugging analysis MUST be placed OUTSIDE the <code_block> tags. 
4. If the user provides a COMPILER ERROR, your sole job is to analyze the log, fix the code, and return the complete corrected source code inside the <code_block> tags. 
5. NEVER use `std::cin` for user input. Your code will run in a headless Docker sandbox and will freeze. You MUST accept all dynamic user inputs via command-line arguments using `int main(int argc, char* argv[])`.
6. STRUCTURAL MANDATE: You MUST strictly adhere to the following C++ architectural template. Do NOT deviate or use nested functions inside main:

<code_block>
#include <iostream>
#include <string>
#include <vector>
// [Include any other necessary standard libraries here]

// ==========================================
// 1. ALL HELPER FUNCTIONS MUST BE DEFINED HERE
// ==========================================

// ==========================================
// 2. MAIN EXECUTION LOGIC
// ==========================================
int main(int argc, char* argv[]) {
    // Parse command-line arguments here
    
    // Execute core logic here
    
    return 0;
}
</code_block>"""
        max_retries = 5

        manager_brain = AIBrain(manager_prompt, model_name="llama3.1")
        coder_brain = AIBrain(coder_prompt, model_name="qwen2.5-coder:7b")
        
        stream_log("[SYSTEM] Manager is drafting the blueprint...")
        blueprint = manager_brain.ask(user_prompt, unload_after=True)

        stream_log(f"HERE IS THE BLUEPRINT :\n{blueprint}")
        stream_log("[SYSTEM] LLaMA unloaded. Qwen taking over VRAM...")

        raw_ai_response = coder_brain.ask(blueprint)

        retries = 0

        while(retries < max_retries):
            with tempfile.TemporaryDirectory() as tempdir:
                full_path = os.path.join(tempdir, "main.cpp")

                clean_code = self.extract_code(raw_ai_response)

                with open(full_path, 'w') as f:
                    f.write(clean_code)
                
                volume_binding = {
                    tempdir: {
                        'bind': '/sandbox',
                        'mode': 'rw'
                    }
                }

                try:
                    stream_log("[SYSTEM] Compiling in Docker Sandbox...")
                    
                    self.client.containers.run(
                        image=self.image,
                        command="g++ main.cpp -o main",
                        remove=True,
                        volumes=volume_binding,
                        working_dir="/sandbox",
                        mem_limit='512m',
                        network_disabled=True,
                    )

                    stream_log("<span style='color: #00ff00;'>[SYSTEM] Compilation successful.</span> Executing binary...")

                    output = self.client.containers.run(
                        image=self.image,
                        command=f"./main {run_args}",
                        remove=True,
                        volumes=volume_binding,
                        working_dir="/sandbox",
                        mem_limit='512m',
                        network_disabled=True,
                    )

                    stream_log("\n=== GENERATED C++ CODE ===")
                    stream_log(clean_code)
                    stream_log("==========================\n")
                    
                    final_msg = f"<span style='color: #00ff00;'>[SUCCESS]</span>\n{output.decode('utf-8')}"
                    stream_log(final_msg)
                    
                    chat(model="qwen2.5-coder:7b", keep_alive=0)

                    MissionLog.objects.create(
                        target_architecture=user_prompt,
                        runtime_vectors=run_args,
                        blueprint=blueprint,
                        source_code=clean_code,
                        status="SUCCESS"
                    )

                    
                    return final_msg
                
                except ContainerError as e:
                    error_logs = e.stderr.decode('utf-8') if e.stderr else str(e)
                    retries += 1

                    # --- THE PYTHON INTERCEPTOR ---
                    ai_hint = ""
                    
                    if "g++" in e.command:
                        # Catch Compilation Errors
                        if "stray" in error_logs or "does not name a type" in error_logs or "Explanation" in error_logs:
                            ai_hint = "CRITICAL: You included conversational text or Markdown outside of the C++ syntax. Strip ALL markdown, explanations, and non-C++ text."
                        elif "is not a member of 'std'" in error_logs or "was not declared in this scope" in error_logs:
                            ai_hint = "CRITICAL: You are missing standard library headers. Ensure you have included <iostream>, <vector>, <string>, <random>, etc."
                        
                        stream_log(f"<span style='color: red;'>[!] Compilation Failed. AI is self-healing (Attempt {retries}/{max_retries})...</span>")
                        stream_log(f"--- COMPILER ERROR ---\n{error_logs.strip()}\n----------------------")
                    
                    else:
                        # Catch Runtime Crashes & Argument Mismatches
                        if "Assertion" in error_logs and "size()" in error_logs:
                            ai_hint = "RUNTIME CRASH: You attempted to access an out-of-bounds index in a string or vector. Ensure you have called .resize() on all rows of your 2D vectors/strings before writing."
                        
                        elif "Usage:" in error_logs or "argc" in error_logs.lower():
                            # THIS FIXES YOUR EXACT BUG
                            ai_hint = f"RUNTIME CRASH: Your code rejected the arguments and printed a Usage error. You MUST adjust your `argc` check to accept the exact number of arguments requested in the blueprint. Do not exit prematurely."
                        
                        else:
                            ai_hint = "RUNTIME CRASH: Your code compiled but crashed during execution. Check your array bounds and pointers."

                        stream_log(f"<span style='color: orange;'>[!] Execution Failed. AI is self-healing (Attempt {retries}/{max_retries})...</span>")
                        stream_log(f"--- RUNTIME ERROR ---\n{error_logs.strip()}\n----------------------")

                    # Inject the specific hint directly into Qwen's recovery prompt
                    recovery_prompt = f"""The C++ code you just provided failed. 

{ai_hint}

CRITICAL INSTRUCTIONS:
1. Analyze the error log below.
2. Return the COMPLETELY FIXED source code strictly inside <code_block> tags.
3. Do NOT apologize, do NOT explain the bug, and do NOT use markdown code fences.

<error_log>
{error_logs}
</error_log>"""
                    
                    stream_log("[SYSTEM] Qwen is analyzing the interceptor telemetry...")
                    raw_ai_response = coder_brain.ask(recovery_prompt)

                except Exception as e:
                    crash_msg = f"<span style='color: red;'>SYSTEM CRASH: {str(e)}</span>"
                    stream_log(crash_msg)
                    chat(model="qwen2.5-coder:7b", keep_alive=0)
                    return crash_msg 

        chat(model="qwen2.5-coder:7b", keep_alive=0)
        fail_msg = f"<span style='color: red;'>FAILED: The AI could not fix the code after {max_retries} attempts.</span>"
        stream_log(fail_msg)

        return fail_msg
        
if __name__ == "__main__":
    sandbox = SandboxOrchestrator()
    
    prompt = input("Enter your prompt to generate the code\n")
    arguments = input("Enter runtime arguments (e.g., '15' for N). Press Enter if none:\n> ")

    print("Running Code...")
    print(sandbox.execute_cpp(prompt, arguments))