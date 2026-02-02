"""
MongoDB database integration for VoiceAst
Stores command history and user preferences
"""
from motor.motor_asyncio import AsyncIOMotorClient
from datetime import datetime
from typing import Optional, List, Dict
import config

class Database:
    """MongoDB database handler"""
    
    def __init__(self):
        self.client: Optional[AsyncIOMotorClient] = None
        self.db = None
        self.connected = False
        
    async def connect(self):
        """Connect to MongoDB"""
        try:
            self.client = AsyncIOMotorClient(config.MONGODB_URL)
            self.db = self.client[config.DATABASE_NAME]
            
            # Test connection
            await self.client.admin.command('ping')
            self.connected = True
            print(f"✓ Connected to MongoDB: {config.DATABASE_NAME}")
            
            # Create indexes
            await self.db.command_history.create_index("timestamp")
            await self.db.user_preferences.create_index("preference_key")
            
        except Exception as e:
            print(f"✗ MongoDB connection failed: {e}")
            print("  Continuing without database (history won't be saved)")
            self.connected = False
    
    async def close(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("✓ MongoDB connection closed")
    
    async def save_command(
        self, 
        command: str, 
        intent: str, 
        response: str, 
        success: bool = True,
        metadata: Optional[Dict] = None
    ):
        """Save command to history"""
        if not self.connected:
            return None
        
        try:
            document = {
                "command": command,
                "intent": intent,
                "response": response,
                "success": success,
                "metadata": metadata or {},
                "timestamp": datetime.utcnow()
            }
            
            result = await self.db.command_history.insert_one(document)
            return str(result.inserted_id)
            
        except Exception as e:
            print(f"Error saving command: {e}")
            return None
    
    async def get_command_history(self, limit: int = 50) -> List[Dict]:
        """Get recent command history"""
        if not self.connected:
            return []
        
        try:
            cursor = self.db.command_history.find().sort(
                "timestamp", -1
            ).limit(limit)
            
            history = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                history.append(doc)
            
            return history
            
        except Exception as e:
            print(f"Error fetching history: {e}")
            return []
    
    async def get_preference(self, key: str) -> Optional[any]:
        """Get user preference"""
        if not self.connected:
            return None
        
        try:
            doc = await self.db.user_preferences.find_one({"preference_key": key})
            return doc.get("value") if doc else None
            
        except Exception as e:
            print(f"Error fetching preference: {e}")
            return None
    
    async def set_preference(self, key: str, value: any):
        """Set user preference"""
        if not self.connected:
            return False
        
        try:
            await self.db.user_preferences.update_one(
                {"preference_key": key},
                {"$set": {"value": value, "updated_at": datetime.utcnow()}},
                upsert=True
            )
            return True
            
        except Exception as e:
            print(f"Error setting preference: {e}")
            return False
    
    async def clear_history(self):
        """Clear all command history"""
        if not self.connected:
            return False
        
        try:
            await self.db.command_history.delete_many({})
            return True
            
        except Exception as e:
            print(f"Error clearing history: {e}")
            return False
    
    async def get_statistics(self) -> Dict:
        """Get usage statistics"""
        if not self.connected:
            return {}
        
        try:
            total_commands = await self.db.command_history.count_documents({})
            successful_commands = await self.db.command_history.count_documents({"success": True})
            
            # Get most common intents
            pipeline = [
                {"$group": {"_id": "$intent", "count": {"$sum": 1}}},
                {"$sort": {"count": -1}},
                {"$limit": 10}
            ]
            
            common_intents = []
            async for doc in self.db.command_history.aggregate(pipeline):
                common_intents.append({
                    "intent": doc["_id"],
                    "count": doc["count"]
                })
            
            return {
                "total_commands": total_commands,
                "successful_commands": successful_commands,
                "success_rate": successful_commands / total_commands if total_commands > 0 else 0,
                "common_intents": common_intents
            }
            
        except Exception as e:
            print(f"Error fetching statistics: {e}")
            return {}

    async def add_memory(self, text: str):
        """Add a memory to the database"""
        if not self.connected:
            return False
        
        try:
            document = {
                "text": text,
                "timestamp": datetime.utcnow()
            }
            await self.db.memories.insert_one(document)
            return True
        except Exception as e:
            print(f"Error adding memory: {e}")
            return False

    async def search_memories(self, query: str = "", limit: int = 5) -> List[str]:
        """
        Get relevant memories.
        For now, returns the most recent memories as a simple 'context window'.
        In future, could use vector search if needed.
        """
        if not self.connected:
            return []
        
        try:
            # Simple implementation: get latest memories
            # We could add text search here if we set up indexes
            cursor = self.db.memories.find().sort("timestamp", -1).limit(limit)
            
            memories = []
            async for doc in cursor:
                memories.append(doc["text"])
            
            return memories
        except Exception as e:
            print(f"Error fetching memories: {e}")
            return []

# Global database instance
db = Database()
