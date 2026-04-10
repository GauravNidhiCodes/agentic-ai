from sqlalchemy import Column, Integer, String, Text
from database import Base
 
 
class Chat(Base):
    __tablename__ = "chats"
 
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True)
    title = Column(String)
    user_input = Column(Text)
    ai_response = Column(Text)
    agent_steps = Column(Text, nullable=True)  # JSON-serialized steps
 
 
class Memory(Base):
    __tablename__ = "memories"
 
    id = Column(Integer, primary_key=True, index=True)
    chat_id = Column(String, index=True)
    content = Column(Text)
    embedding_id = Column(Integer, nullable=True)  # FAISS index position
 