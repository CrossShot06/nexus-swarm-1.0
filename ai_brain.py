
import re

from ollama import ChatResponse
from ollama import chat

class AIBrain():

    def __init__(self,system_prompt,model_name):
        
        self.model = model_name
        self.messages = [
            {"role":"system","content":system_prompt}
                         ]
    
    def ask(self,user_prompt,unload_after=False):

        self.messages.append({"role":"user","content":user_prompt})

        keep_alive_val = 0 if unload_after else "5m"

        response : ChatResponse = chat(
            model = self.model,
            messages=self.messages,
            keep_alive=keep_alive_val
        )

        ai_reply = response['message']['content']

        self.messages.append({"role":"assistant","content":ai_reply})

        
        
        match = re.search(r'<code_block>(.*?)</code_block>', ai_reply, re.DOTALL | re.IGNORECASE)
        
        if match:
            clean_code = match.group(1)
        else:
            clean_code = ai_reply 
            
       
        clean_code = re.sub(r'```[a-zA-Z\+]*', '', clean_code)
        
        clean_code = clean_code.replace('```', '')
        
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