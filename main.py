import docker
import tempfile
import os

from ai_brain import AIBrain
from docker.errors import ContainerError

class SandboxOrchestrator :

    def __init__(self) :

        self.image = "nexus-swarm:latest"
        self.client = docker.from_env()

    def execute_cpp(self,user_prompt):

        max_retries = 3

        brain = AIBrain()

        code_string = brain.ask(user_prompt)

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
                        command="sh -c 'g++ main.cpp -o main && ./main'",
                        remove=True,
                        volumes=volume_binding,
                        working_dir="/sandbox",
                        mem_limit='512m',
                        network_disabled=True,
                    )

                    return f"SUCCESS:\n{output.decode('utf-8')}"
                
                except ContainerError as e:

                    retries=retries+1

                    error_logs = e.stderr.decode('utf-8') if e.stderr else str(e)

                    print(f"\n[!] Compilation Failed. AI is self-healing (Attempt {retries}/3)...")

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
                    
                    code_string = brain.ask(recovery_prompt)

                except Exception as e:

                    return f"SYSTEM CRASH: {str(e)}"
                
        return "FAILED: The AI could not fix the code after 3 attempts."

        
        
                
if __name__ == "__main__" :
    sandbox = SandboxOrchestrator()
    
    prompt = input("Enter your prompt to generate the code")


    print("Running Good Code...")
    print(sandbox.execute_cpp(prompt))