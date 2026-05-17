import docker

print("Connecting to Python's Docker vault...")
client = docker.from_env()

print('Building image.....')
client.images.build(path='.',tag='nexus-swarm:latest')

print("SUCCESS: Image built")
