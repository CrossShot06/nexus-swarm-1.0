import asyncio
from django.http import StreamingHttpResponse,JsonResponse
from django.shortcuts import render
from main import SandboxOrchestrator 
from .models import MissionLog

def swarm_ui(request):
    return render(request, 'index.html')

async def real_swarm_stream(request):

    user_prompt = request.GET.get('prompt', 'Write a C++ program that prints Hello World')
    run_args = request.GET.get('args', '')

    queue = asyncio.Queue()
    loop = asyncio.get_running_loop()

    def stream_callback(message):

        loop.call_soon_threadsafe(queue.put_nowait, message)

    async def event_generator():

        orchestrator = SandboxOrchestrator()
        
        task = asyncio.create_task(
            asyncio.to_thread(orchestrator.execute_cpp, user_prompt, run_args, stream_callback)
        )

        while True:
            message = await queue.get()

            
            formatted_msg = message.replace('\n', '<br>')
            yield f"data: {formatted_msg}\n\n"

            if task.done() and queue.empty():
                yield "data: [DONE]\n\n"
                break

    return StreamingHttpResponse(event_generator(), content_type='text/event-stream')

def archive_api(request):
    
    logs = MissionLog.objects.all().order_by('-created_at')[:10]
    data = []
    
    for log in logs:
        data.append({
            "id": log.id,
            "prompt": log.target_architecture,
            "args": log.runtime_vectors,
            "code": log.source_code,
            "status": log.status,
            "date": log.created_at.strftime("%H:%M:%S | %Y-%m-%d")
        })
        
    return JsonResponse({"archives": data})