
import re

from ollama import ChatResponse
from ollama import chat

class AIBrain():

    def __init__(self,role="""You are an automated C++ backend compilation assistant. 
Your absolute priority is to generate syntactically perfect, highly optimized C++ code.

CRITICAL RULES:
1. You MUST place all executable C++ code strictly inside <code_block> and </code_block> tags.
2. Do NOT use markdown code fences (like ```cpp) inside or outside the tags.
3. Any explanations, thought processes, or debugging analysis MUST be placed OUTSIDE the <code_block> tags.
4. If the user provides a COMPILER ERROR, your sole job is to analyze the log, fix the code, and return the complete corrected source code inside the <code_block> tags.
5. NEVER use `std::cin` for user input. Your code will run in a headless Docker sandbox and will freeze. You MUST accept all dynamic user inputs via command-line arguments using `int main(int argc, char* argv[])"""):
        
        self.model = "llama3.1"
        self.messages = [
            {"role":"system","content":role}
                         ]
    
    def ask(self,user_prompt):

        self.messages.append({"role":"user","content":user_prompt})

        response : ChatResponse = chat(
            model = self.model,
            messages=self.messages
        )

        ai_reply = response['message']['content']

        self.messages.append({"role":"assistant","content":ai_reply})

        
        
        match = re.search(r'<code_block>(.*?)</code_block>', ai_reply, re.DOTALL | re.IGNORECASE)
        
        if match:
            clean_code = match.group(1)
        else:
            clean_code = ai_reply 
            
       
        clean_code = re.sub(r'```[a-zA-Z\+]*', '', clean_code)
        
       
        if not match:
             if "#include" in clean_code:
                 clean_code = clean_code[clean_code.find("#include"):]
             elif "int main" in clean_code:
                 clean_code = clean_code[clean_code.find("int main"):]

        return clean_code.strip()
        
if __name__ == "__main__":
    print("Initializing Brain...")
    brain = AIBrain()
    print("Sending prompt...")
    code = brain.ask("Write a C++ program that prints out the first 5 numbers of the Fibonacci sequence.")
    print("\n=== EXTRACTED CODE ===")
    print(code)