import docker
import tempfile
import os

class SandboxOrchestrator :

    def __init__(self) :

        self.image = "nexus-swarm:latest"
        self.client = docker.from_env()

    def execute_cpp(self,code_string):

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
            
            except Exception as e:
                return f"COMPILER ERROR:\n{e.stderr.decode('utf-8')}"
            
if __name__ == "__main__" :
    sandbox = SandboxOrchestrator()
    
    good_code = """
    #include <iostream>
    using namespace std;
    int main() {
        cout << "Hello from inside the Docker volume mount!" << endl;
        return 0;
    }
    """
    print("Running Good Code...")
    print(sandbox.execute_cpp(good_code))