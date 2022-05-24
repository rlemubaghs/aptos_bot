import os
from typing import List
from datetime import datetime, timedelta

import supabase
from node_layout import NodeList


class Node:

    def __init__(self, supabase_url: str, supabase_key: str) -> None:
        self.supabase = supabase.create_client(supabase_url, supabase_key)

    def initiate(supabase_url: str, supabase_key: str) -> 'Node':
        return Node(supabase_url, supabase_key)

    def update_nodelist(self, node_list: NodeList):
        current_nodes = (
            self.supabase.table(os.environ.get('SUPABASE_TABLE')).
                select("*", count="exact").
                eq("tg_chat_id", node_list.tg_chat_id).
                execute()
        )
        return (
            self.supabase.
                table(os.environ.get('SUPABASE_TABLE')).
                upsert(node_list.to_dict()).execute()
        )

    def delete_node(self, node_list: NodeList):
        return (
            self.supabase.table(os.environ.get('SUPABASE_TABLE')).
                delete().
                eq("tg_chat_id", node_list.tg_chat_id).
                eq("ip", node_list.ip).
                execute()
        )

    def get_available_nodes(self, tg_chat_id: int) -> List[NodeList]:
        available_nodes = (
            self.supabase.table(os.environ.get('SUPABASE_TABLE'))
                .select("*")
                .eq("tg_chat_id", tg_chat_id)
                .execute()
        )
        return [NodeList.from_dict(a) for a in available_nodes.data]

    def get_alarm_node(self) -> List[NodeList]:
        alarm_nodes = (
            self.supabase.table(os.environ.get('SUPABASE_TABLE'))
                .select("*")
                .is_("status", False)
                .execute()
        )
        nodes = (NodeList.from_dict(a) for a in alarm_nodes.data)
        return [a for a in nodes if a.alarm_sent < a.modified]

    def get_check_nodes(self, max_age: timedelta) -> List[NodeList]:
        max_age = int((datetime.utcnow() - max_age).timestamp())
        available_nodes = (
            self.supabase.table(os.environ.get('SUPABASE_TABLE'))
            .select("*")
            .lt("checked", max_age)
            .execute()
        )
        return [NodeList.from_dict(a) for a in available_nodes.data]