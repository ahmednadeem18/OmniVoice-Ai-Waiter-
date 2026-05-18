from fastapi import FastAPI, WebSocket, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import os
import json
import asyncio
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import jwt
from dotenv import load_dotenv
from supabase import create_client, Client
import logging

# Import AI models
try:
    from faster_whisper import WhisperModel
    from llama_cpp import Llama
    import edge_tts
except ImportError:
    pass

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastAPI
app = FastAPI(title="OmniVoice AI Waiter", version="1.0.0")

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment Variables
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
JWT_SECRET = os.getenv("JWT_SECRET", "your-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

# Initialize Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Initialize AI Models (lazy load)
whisper_model = None
llama_model = None

def get_whisper_model():
    global whisper_model
    if whisper_model is None:
        whisper_model = WhisperModel("tiny.en", device="cpu", compute_type="int8")
    return whisper_model

def get_llama_model():
    global llama_model
    if llama_model is None:
        llama_model = Llama(
            model_path="../model_bins/Llama-3.2-1B-Instruct-Q4_K_M.gguf",
            n_ctx=512,
            n_threads=4
        )
    return llama_model

# ==================== JWT UTILITIES ====================

def create_access_token(customer_id: int) -> str:
    """Generate JWT token for customer"""
    payload = {
        "customer_id": customer_id,
        "exp": datetime.utcnow() + timedelta(hours=JWT_EXPIRATION_HOURS),
        "iat": datetime.utcnow()
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    """Verify and decode JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== AUTHENTICATION ROUTES ====================

@app.post("/auth/login")
async def login(phone_number: str, password: str):
    """Customer login endpoint"""
    try:
        response = supabase.table("customers").select("*").eq("phone_number", phone_number).execute()
        
        if not response.data:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        customer = response.data[0]
        # In production, use proper password hashing (bcrypt)
        if customer["password_hash"] != password:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_access_token(customer["id"])
        return {
            "access_token": token,
            "token_type": "bearer",
            "customer_id": customer["id"],
            "name": customer["name"]
        }
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/auth/register")
async def register(phone_number: str, name: str, password: str, delivery_address: str = None):
    """Customer registration endpoint"""
    try:
        response = supabase.table("customers").insert({
            "phone_number": phone_number,
            "name": name,
            "password_hash": password,  # In production, hash this
            "default_delivery_address": delivery_address
        }).execute()
        
        if response.data:
            customer = response.data[0]
            token = create_access_token(customer["id"])
            return {
                "access_token": token,
                "token_type": "bearer",
                "customer_id": customer["id"]
            }
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        raise HTTPException(status_code=400, detail="Registration failed")

# ==================== MENU ROUTES ====================

@app.get("/menu/categories")
async def get_categories():
    """Get all menu categories"""
    try:
        response = supabase.table("categories").select("*").execute()
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error fetching categories: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/menu/items")
async def get_menu_items(category_id: int = None):
    """Get menu items, optionally filtered by category"""
    try:
        query = supabase.table("menu_items").select("*").eq("is_available", True)
        
        if category_id:
            query = query.eq("category_id", category_id)
        
        response = query.execute()
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error fetching menu items: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/menu/deals")
async def get_deals():
    """Get active promotional deals"""
    try:
        response = supabase.table("deals").select("*").eq("is_active", True).execute()
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error fetching deals: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== ORDER ROUTES ====================

@app.get("/orders/history")
async def get_order_history(token: str):
    """Get customer order history"""
    try:
        payload = verify_token(token)
        customer_id = payload["customer_id"]
        
        response = supabase.table("orders").select(
            "*, order_items(*, menu_items(*), deals(*), order_item_modifiers(*))"
        ).eq("customer_id", customer_id).order("created_at", desc=True).execute()
        
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error fetching order history: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== WEBSOCKET VOICE GATEWAY ====================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.sessions: Dict[str, dict] = {}
    
    async def connect(self, session_id: str, websocket: WebSocket):
        await websocket.accept()
        self.active_connections[session_id] = websocket
        self.sessions[session_id] = {
            "created_at": datetime.utcnow(),
            "current_step": "welcome",
            "customer_id": None,
            "order_items": [],
            "delivery_address": None
        }
        logger.info(f"Client {session_id} connected")
    
    async def disconnect(self, session_id: str):
        if session_id in self.active_connections:
            del self.active_connections[session_id]
        if session_id in self.sessions:
            del self.sessions[session_id]
        logger.info(f"Client {session_id} disconnected")
    
    async def send_personal(self, session_id: str, data: dict):
        if session_id in self.active_connections:
            await self.active_connections[session_id].send_json(data)

manager = ConnectionManager()

@app.websocket("/call/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    """Main WebSocket endpoint for voice calls"""
    await manager.connect(session_id, websocket)
    
    try:
        while True:
            data = await websocket.receive_json()
            
            if data["type"] == "audio_chunk":
                # Process audio chunk
                audio_data = data["audio"]
                
                # STT: Convert audio to text
                try:
                    whisper = get_whisper_model()
                    segments, info = whisper.transcribe(audio_data, language="en")
                    user_text = " ".join([segment.text for segment in segments])
                except:
                    user_text = ""
                
                if user_text:
                    # LLM: Process user intent
                    session = manager.sessions[session_id]
                    llm_response = await process_user_input(user_text, session)
                    
                    # TTS: Generate speech
                    try:
                        tts_audio = await generate_speech(llm_response["spoken_response"])
                        await manager.send_personal(session_id, {
                            "type": "audio_response",
                            "audio": tts_audio,
                            "intent": llm_response["intent"],
                            "data": llm_response.get("data", {})
                        })
                    except Exception as e:
                        logger.error(f"TTS error: {str(e)}")
            
            elif data["type"] == "session_init":
                # Initialize session with customer metadata
                manager.sessions[session_id]["customer_id"] = data.get("customer_id")
                if data.get("delivery_address"):
                    manager.sessions[session_id]["delivery_address"] = data["delivery_address"]
                
                # Send welcome message
                welcome_msg = "Welcome to OmniVoice AI. I am your virtual waiter. How can I help you today?"
                tts_audio = await generate_speech(welcome_msg)
                await manager.send_personal(session_id, {
                    "type": "welcome",
                    "audio": tts_audio,
                    "message": welcome_msg
                })
    
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
    finally:
        await manager.disconnect(session_id)

async def process_user_input(user_text: str, session: dict) -> dict:
    """Process user input through LLM based on session state"""
    try:
        llama = get_llama_model()
        
        # Build context based on current step
        if session["current_step"] == "welcome":
            prompt = f"Customer says: '{user_text}'. Extract their name and greet them warmly. Respond in JSON format with 'name', 'spoken_response', and 'intent': 'capture_name'."
        elif session["current_step"] == "ordering":
            prompt = f"Customer says: '{user_text}'. Parse food order items. Respond in JSON with 'items' array containing 'name', 'quantity', 'modifiers', 'spoken_response', and 'intent': 'add_item' or 'checkout'."
        elif session["current_step"] == "address":
            prompt = f"Customer says: '{user_text}'. Extract delivery address. Respond in JSON with 'address', 'spoken_response', and 'intent': 'set_address'."
        elif session["current_step"] == "confirming":
            prompt = f"Customer says: '{user_text}'. Confirm order or ask for changes. Respond in JSON with 'confirmed' (bool), 'spoken_response', and 'intent': 'confirm' or 'modify'."
        else:
            prompt = user_text
        
        response = llama(prompt, max_tokens=200, temperature=0.7)
        
        try:
            result = json.loads(response["choices"][0]["text"])
        except:
            result = {"spoken_response": "I didn't understand that. Could you please repeat?", "intent": "retry"}
        
        return result
    except Exception as e:
        logger.error(f"LLM processing error: {str(e)}")
        return {"spoken_response": "Sorry, I encountered an error. Please try again.", "intent": "error"}

async def generate_speech(text: str) -> str:
    """Generate speech from text using Edge TTS"""
    try:
        communicate = edge_tts.Communicate(text=text, voice="en-IN-PrabhatNeural", rate="+25%")
        import io
        audio_buffer = io.BytesIO()
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_buffer.write(chunk["data"])
        return audio_buffer.getvalue().hex()
    except Exception as e:
        logger.error(f"TTS error: {str(e)}")
        return ""

# ==================== ADMIN ROUTES ====================

@app.get("/admin/orders")
async def get_all_orders(token: str):
    """Get all orders for admin dashboard"""
    try:
        payload = verify_token(token)
        # TODO: Verify admin role
        
        response = supabase.table("orders").select(
            "*, order_items(*, menu_items(*), order_item_modifiers(*)), customers(name, phone_number)"
        ).order("created_at", desc=True).execute()
        
        return {"data": response.data}
    except Exception as e:
        logger.error(f"Error fetching admin orders: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.put("/admin/orders/{order_id}/status")
async def update_order_status(order_id: int, status: str, token: str):
    """Update order status"""
    try:
        payload = verify_token(token)
        # TODO: Verify admin role
        
        response = supabase.table("orders").update(
            {"status": status, "updated_at": datetime.utcnow().isoformat()}
        ).eq("id", order_id).execute()
        
        return {"success": True, "data": response.data}
    except Exception as e:
        logger.error(f"Error updating order status: {str(e)}")
        raise HTTPException(status_code=500, detail="Internal server error")

# ==================== HEALTH CHECK ====================

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)