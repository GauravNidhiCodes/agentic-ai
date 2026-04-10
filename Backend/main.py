from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv

from database import SessionLocal, engine
import models
from agent import AgentExecutor

models.Base.metadata.create_all(bind=engine)
load_dotenv()

app = FastAPI(title="Agentic AI Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

agent_executor = AgentExecutor()


class ChatRequest(BaseModel):
    user_input: str
    chat_id: str = "default"


@app.post("/chat")
async def chat(req: ChatRequest):
    db = SessionLocal()
    try:
        # Fetch short-term memory (last 6 exchanges)
        history = db.query(models.Chat).filter(
            models.Chat.chat_id == req.chat_id
        ).order_by(models.Chat.id.desc()).limit(6).all()
        history = list(reversed(history))

        short_term = [
            {"role": "user", "content": c.user_input}
            for c in history
        ] + [
            {"role": "assistant", "content": c.ai_response}
            for c in history
        ]

        # Run agent loop
        result = await agent_executor.run(
            user_input=req.user_input,
            chat_id=req.chat_id,
            history=short_term,
        )

        # Persist to DB
        title = req.user_input[:40] if not history else history[0].title
        entry = models.Chat(
            chat_id=req.chat_id,
            title=title,
            user_input=req.user_input,
            ai_response=result["answer"],
            agent_steps=str(result["steps"]),
        )
        db.add(entry)
        db.commit()

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()


@app.get("/history")
def history(chat_id: str):
    db = SessionLocal()
    try:
        chats = db.query(models.Chat).filter(
            models.Chat.chat_id == chat_id
        ).all()
        return [
            {
                "user": c.user_input,
                "ai": c.ai_response,
                "steps": c.agent_steps,
            }
            for c in chats
        ]
    finally:
        db.close()


@app.get("/chats")
def get_chats():
    db = SessionLocal()
    try:
        chats = db.query(models.Chat).all()
        unique = {}
        for c in chats:
            unique[c.chat_id] = c.title
        return [{"chat_id": cid, "title": t} for cid, t in unique.items()]
    finally:
        db.close()


@app.get("/memory/{chat_id}")
def get_memory(chat_id: str):
    """Return semantic memory snippets for a chat."""
    from memory import MemoryManager
    mm = MemoryManager()
    results = mm.search(chat_id, "summary", k=5)
    return {"memories": results}
