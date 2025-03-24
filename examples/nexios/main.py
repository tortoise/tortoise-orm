# main.py
from tortoise.contrib.nexios import register_tortoise
from nexios import get_application
from nexios.http import Request, Response
from models import Task
import uvicorn

app = get_application()

@app.get("/tasks")
async def list_tasks(req: Request, res: Response):
    tasks = await Task.all()
    return res.json([{
        "id": task.id,
        "title": task.title,
        "description": task.description
    } for task in tasks])


@app.get("/tasks/{task_id}")
async def get_task(req: Request, res: Response):
    task_id: int = req.path_params.task_id
    task = await Task.get_or_none(id=task_id)
    if not task:
        return res.status(404).json({"error": "Task not found"})
    return res.json({
        "id": task.id,
        "title": task.title,
        "description": task.description
    })


@app.post("/tasks")
async def create_task(req: Request, res: Response):
    request_data = await req.json
    if not request_data.get("title"):
        return res.status(400).json({"error": "Title is required"})
    
    task = await Task.create(
        title=request_data["title"],
        description=request_data.get("description")
    )
    return res.json({
        "id": task.id,
        "title": task.title,
        "description": task.description
    }).status(201)


@app.put("/tasks/{task_id}")
async def update_task(req: Request, res: Response):
    task_id: int = req.path_params.task_id
    
    task = await Task.get_or_none(id=task_id)
    if not task:
        return res.status(404).json({"error": "Task not found"})
    
    request_data = await req.json
    task.title = request_data.get("title", task.title)
    task.description = request_data.get("description", task.description)
    await task.save()
    
    return res.json({
        "id": task.id,
        "title": task.title,
        "description": task.description
    })


@app.delete("/tasks/{task_id}")
async def delete_task(req: Request, res: Response, task_id: int):
    task = await Task.get_or_none(id=task_id)
    if not task:
        return res.status(404).json({"error": "Task not found"})
    
    await task.delete()
    return res.json({"message": "Task deleted"})


register_tortoise(
    app,
    db_url="sqlite://:memory:",
    modules={"models": ["models"]},
    generate_schemas=True
)


if __name__ == "__main__":
    uvicorn.run(app, port=9000)