import docker
import tempfile
import os

from ollama import chat

from ai_brain import AIBrain
from docker.errors import ContainerError

class SandboxOrchestrator :

    def __init__(self) :

        self.image = "nexus-swarm:latest"
        self.client = docker.from_env()

    def execute_cpp(self,user_prompt,run_args=""):
        

        manager_prompt = """You are a Senior C++ Software Architect. 
                            Your job is to analyze the user's request and write a strict, step-by-step technical blueprint for a junior developer.
                            Detail the exact logic flow, required functions, and edge cases.
                            CRITICAL: Do NOT write any C++ code. Only write the architecture plan in plain text.
                            CRITICAL: Remind the developer they must use `argv` for dynamic inputs, not `std::cin`."""


        coder_prompt = """You are an automated C++ backend compilation assistant. 
                        Your absolute priority is to generate syntactically perfect, highly optimized C++ code.

                        CRITICAL RULES:
                        1. You MUST place all executable C++ code strictly inside <code_block> and </code_block> tags.
                        2. Do NOT use markdown code fences (like ```cpp) inside or outside the tags.
                        3. Any explanations, thought processes, or debugging analysis MUST be placed OUTSIDE the <code_block> tags.
                        4. If the user provides a COMPILER ERROR, your sole job is to analyze the log, fix the code, and return the complete corrected source code inside the <code_block> tags.
                        5. NEVER use `std::cin` for user input. Your code will run in a headless Docker sandbox and will freeze. You MUST accept all dynamic user inputs via command-line arguments using `int main(int argc, char* argv[])"""



        max_retries = 5

        manager_brain = AIBrain(manager_prompt,model_name="llama3.1")

        coder_brain = AIBrain(coder_prompt,model_name="qwen2.5-coder:7b")

        blueprint = manager_brain.ask(user_prompt,unload_after=True)

        print(f"HERE IS THE BLUEPRINT : \n {blueprint}")

        code_string = coder_brain.ask(blueprint)

        retries = 0

        while(retries<max_retries):

            with tempfile.TemporaryDirectory() as tempdir :

                full_path = os.path.join(tempdir,"main.cpp")

                with open(full_path,'w') as f :
                    f.write(code_string)
                
                volume_binding = {
                    tempdir : {
                        'bind' : '/sandbox',
                        'mode' : 'rw'
                    }
                }

                try :
                    output = self.client.containers.run(
                        image=self.image,
                        command=f"sh -c 'g++ main.cpp -o main && ./main {run_args}'",
                        remove=True,
                        volumes=volume_binding,
                        working_dir="/sandbox",
                        mem_limit='512m',
                        network_disabled=True,
                    )

                    print("\n=== GENERATED C++ CODE ===")
                    print(code_string)
                    print("==========================\n")

                    return f"SUCCESS:\n{output.decode('utf-8')}"
                
                except ContainerError as e:

                    retries=retries+1

                    error_logs = e.stderr.decode('utf-8') if e.stderr else str(e)

                    print(f"\n[!] Compilation Failed. AI is self-healing (Attempt {retries}/{max_retries})...")

                    print(f"--- COMPILER ERROR ---\n{error_logs.strip()}\n----------------------")

                    recovery_prompt = f"""The C++ code you just provided failed to compile. 

                                            Your task is to fix the errors and rewrite the entire file.

                                            CRITICAL INSTRUCTIONS:
                                            1. Analyze the compiler error log below.
                                            2. Return the COMPLETELY FIXED source code. Do not just return the changed lines; return the entire working file.
                                            3. You MUST wrap the fixed code inside <code_block> and </code_block> tags.
                                            4. Do NOT apologize, do NOT explain the bug, and do NOT use markdown code fences.

                                            <error_log>
                                            {error_logs}
                                            </error_log>"""
                    
                    code_string = coder_brain.ask(recovery_prompt)

                except Exception as e:

                    return f"SYSTEM CRASH: {str(e)}"
                
        chat(model="qwen2.5-coder:7b", keep_alive=0)
                
        return f"FAILED: The AI could not fix the code after {max_retries} attempts."

        
        
                
if __name__ == "__main__" :
    sandbox = SandboxOrchestrator()
    
    prompt = input("Enter your prompt to generate the code\n")

    arguments = input("Enter runtime arguments (e.g., '15' for N). Press Enter if none:\n> ")

    print("Running Code...")
    print(sandbox.execute_cpp(prompt,arguments))