"""
This repository and its contents are created and owned by github.com/Joelkb, and it is a private project maintained by him.
Unauthorized copying, modification, distribution, or any other use of this code or its contents is strictly prohibited without explicit permission from the owner.
For inquiries or requests regarding the use of this code, please contact github.com/Joelkb directly

Database interaction layer for Ellie Forward Bot.
"""

from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import DuplicateKeyError
from config import configVars
from datetime import datetime, timezone
import logging
import uuid

logger = logging.getLogger(__name__)


class DataBase:
    def __init__(self):
        self._client = AsyncIOMotorClient(configVars.DB_URI)
        self.db = self._client["ForwardBot"]

        self.users = self.db.users
        self.setgs = self.db.settings

        self.jobs = self.db.jobs
        self.files = self.db.files          # physical files
        self.deliveries = self.db.deliveries  # per-target delivery state
        self.parts = self.db.partitions

    async def ensure_indexes(self) -> None:
        await self.deliveries.create_index(
            [("file_id", 1), ("target_chat", 1)],
            unique=True,
            name="uniq_file_per_target"
        )

        await self.deliveries.create_index(
            [("job_id", 1), ("forwarded", 1)],
            name="job_forwarding_lookup"
        )

    async def get_job_progress(self, job_id: str) -> dict:
        total = await self.deliveries.count_documents({"job_id": job_id})
        done = await self.deliveries.count_documents({
            "job_id": job_id,
            "forwarded": True
        })
        failed_parts = await self.parts.count_documents({
            "job_id": job_id,
            "status": "failed"
        })

        return {
            "total": total,
            "done": done,
            "pending": total - done,
            "failed_parts": failed_parts
        }

    async def create_partitions(self, job_id: str, workers: list, is_direct: bool = False, skip: int = 0, l_msg_id: int = 0) -> None:
        docs = self.deliveries.find(
            {"job_id": job_id},
            {"last_source.msg_id": 1}
        )
        
        msg_ids = sorted([d["last_source"]["msg_id"] async for d in docs]) if not is_direct else list(range(int(skip) + 1, int(l_msg_id) + 1))
        if not msg_ids:
            return

        total = len(msg_ids)
        chunk = max(1, total // len(workers))

        for i, worker in enumerate(workers):
            start_idx = i * chunk
            if start_idx >= total:
                break

            start = msg_ids[start_idx]
            end = msg_ids[-1] if i == len(workers) - 1 else msg_ids[min((i+1)*chunk - 1, total - 1)]

            await self.parts.insert_one({
                "_id": f"{job_id}_{i}",
                "job_id": job_id,
                "worker": worker,
                "start_msg_id": start,
                "end_msg_id": end,
                "current_msg_id": start,
                "status": "pending",
                "progress": 0,
                "total": end - start + 1,
                "error": None,
                "updated_at": datetime.now(timezone.utc)
            })

    async def partitions_exist(self, job_id: str) -> bool:
        return await self.parts.count_documents({"job_id": job_id}) > 0
    
    async def remove_job(self, job_id: str) -> None:
        await self.jobs.delete_one({"_id": job_id})
        await self.parts.delete_many({"job_id": job_id})
        return await self.deliveries.delete_many({"job_id": job_id})

    async def save_media(self, unique_id, job_id, msg_id, f_name, f_size, cap, s_chat, t_chat) -> bool:
        now = datetime.now(timezone.utc)

        # Updates sources AND gets the current list of who has received it
        file_doc = await self.files.find_one_and_update(
            {"_id": unique_id},
            {
                "$addToSet": {"sources": {"chat_id": s_chat, "msg_id": msg_id}},
                "$setOnInsert": {
                    "created_at": now, 
                    "forwarded_to": []
                }
            },
            upsert=True,
            return_document=True
        )

        if t_chat in file_doc.get("forwarded_to", []):
            logger.info(f"Target already received | file={unique_id} | target={t_chat}")
            return False

        try:
            await self.deliveries.update_one(
                {"file_id": unique_id, "job_id": job_id, "target_chat": t_chat},
                {
                    "$setOnInsert": {
                        "caption": cap, "file_size": f_size, "file_name": f_name,
                        "last_source": {"chat_id": s_chat, "msg_id": msg_id},
                        "created_at": now, "forwarded": False
                    }
                },
                upsert=True
            )
        except DuplicateKeyError:
            logger.info(f"Delivery already exists | file={unique_id} | job={job_id} | target={t_chat}")
            return False

        return True

    async def insert_job(
        self,
        source_id: int,
        l_msg_id: int,
        status: str,
        t_chat: int,
        switch_chats: list,
        w_client: list,
        p_chat_id: int,
        p_msg_id: int,
        skip: int = 0,
        is_direct: bool = False
    ) -> str:
        job_id = uuid.uuid4().hex

        await self.jobs.insert_one({
            "_id": job_id,
            "source_id": source_id,
            "l_msg_id": l_msg_id,
            "status": status,  # indexing | forwarding | resuming | completed
            "t_chat": t_chat,
            "switch_chats": switch_chats,
            "worker_clients": w_client,
            "is_direct": is_direct,

            # indexing resume fields
            "index_cursor": skip,           # last processed message id / offset
            "indexed_count": 0,
            "duplicate_count": 0,
            "deleted_count": 0,
            "non_media_count": 0,
            "error_count": 0,

            # progress message
            "progress_chat_id": p_chat_id,
            "progress_msg_id": p_msg_id,

            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc)
        })

        return job_id
    
    async def update_job_status(self, job_id: str, status: str) -> None:
        await self.jobs.update_one(
            {"_id": job_id},
            {"$set": {"status": status}}
        )

    async def get_pending_deliveries(self, job_id: str, t_chat: int):
        return self.deliveries.find({
            "job_id": job_id,
            "target_chat": t_chat,
            "forwarded": False
        })

    async def mark_delivered(self, delivery_id):
        delivery = await self.deliveries.find_one({"_id": delivery_id})
        if not delivery:
            return
        elif delivery["forwarded"]:
            return

        await self.deliveries.update_one(
            {"_id": delivery_id},
            {"$set": {"forwarded": True}}
        )

        await self.files.update_one(
            {"_id": delivery["file_id"]},
            {"$addToSet": {"forwarded_to": delivery["target_chat"]}}
        )

        await self.setgs.update_one(
            {"_id": "settings"},
            {
                "$inc": {
                    "t_files": 1,
                    "t_size": delivery["file_size"]
                }
            },
            upsert=True
        )

    async def get_user(self, id: int):
        return await self.users.find_one({"_id": id})

    async def add_or_update_user(self, id: int, is_admin: bool) -> None:
        if is_admin and id not in configVars.ADMINS:
            configVars.ADMINS.append(id)

        await self.users.update_one(
            {"_id": id},
            {"$set": {"is_admin": is_admin}},
            upsert=True
        )

    async def get_admins(self) -> list:
        cursor = self.users.find({"is_admin": True})
        return [doc["_id"] async for doc in cursor]

    async def get_settings(self) -> dict:
        doc = await self.setgs.find_one({"_id": "settings"})
        if not doc:
            doc = {
                "custom_btn": False,
                "custom_caption": False,
                "limit": 0,
                "skip": 0,
                "cap_template": "",
                "btn_template": "",
                "worker_clients": [],
                "t_files": 0,
                "t_size": 0,
                "target_chats": []
            }
        return doc

    async def update_settings(self, _dict: dict) -> None:
        await self.setgs.update_one(
            {"_id": "settings"},
            {"$set": _dict},
            upsert=True
        )

db = DataBase()