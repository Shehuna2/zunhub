# p2p/consumers.py

import json
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth import get_user_model
from .models import DepositOrder

User = get_user_model()

class OrderConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # 1. Grab order_id and user from scope
        self.order_id = self.scope["url_route"]["kwargs"]["order_id"]
        self.user = self.scope["user"]

        # 2. Load the order in a thread, not in the event loop
        try:
            self.order = await database_sync_to_async(
                DepositOrder.objects.select_related("buyer", "sell_offer__merchant")
                                   .get
            )(id=self.order_id)
        except DepositOrder.DoesNotExist:
            return await self.close()

        # 3. Permission check (pure Python; no new ORM calls)
        if self.user != self.order.buyer and self.user != self.order.sell_offer.merchant:
            return await self.close()

        # 4. Join the group
        await self.channel_layer.group_add(f"order_{self.order_id}", self.channel_name)
        await self.accept()

    async def disconnect(self, code):
        await self.channel_layer.group_discard(f"order_{self.order_id}", self.channel_name)

    # Handler for messages sent to the group
    async def order_status_update(self, event):
        # event["data"] is already a dict with keys "event" and "status"
        await self.send(text_data=json.dumps(event["data"]))
