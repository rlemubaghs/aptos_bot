import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta
from time import sleep

from node_aptos import AptosNode
from node_layout import NodeList
from node_database import Node


class UpdateNodeList:
    def __init__(self, threads: int, database: Node, target: AptosNode,
                 update_frequency: timedelta = timedelta(seconds=10),
                 max_check_age: timedelta = timedelta(minutes=6)) -> None:
        self.executor = ThreadPoolExecutor(max_workers=threads)
        self.database = database
        self.target = target
        self.update_frequency = update_frequency
        self.max_check_age = max_check_age

    @staticmethod
    def default() -> 'UpdateNodeList':
        return UpdateNodeList(
            threads=int(os.environ.get('APTOS_THREADS')),
            database=Node.initiate(os.environ.get('SUPABASE_URL'), os.environ.get('SUPABASE_KEY')),
            target=AptosNode(
                host=os.environ.get('APTOS_TARGET_HOST'),
                proto=os.environ.get('APTOS_TARGET_PROTO'),
                api_port=int(os.environ.get('APTOS_TARGET_PORT')),
                metrics_port=None,
                seed_port=None
            )
        )

    def run(self):
        while True:
            for node_check in self.database.get_check_nodes(self.max_check_age):
                self.executor.submit(self.__update_node_status, node_check)
            sleep(self.update_frequency.total_seconds())

    def __update_node_status(self, node_list: NodeList):
        self.target.update()
        node = AptosNode(host=node_list.ip,
                         api_port=node_list.api_port,
                         metrics_port=node_list.metrics_port,
                         seed_port=node_list.seed_port)
        node.update()
        errors = []

        if not node.api_port_opened:
            errors.append('API port: closed')
        elif node.chain_id and node.chain_id != self.target.chain_id:
            errors.append('Node out of date')
        if not node.seed_port_opened:
            errors.append('Seed port: closed')
        if not node.metrics_port_opened:
            errors.append('Metrics port: closed')
        elif node.synced is False:
            errors.append('Out of sync')

        errors.sort()

        status = not errors
        has_modified = (
                node_list.status is None
                or status != node_list.status
                or errors != node_list.errors
        )
        node_list.status = status
        node_list.checked = int(datetime.utcnow().timestamp())
        node_list.modified = int(datetime.utcnow().timestamp()) if has_modified else node_list.modified
        node_list.errors = errors
        self.database.update_nodelist(node_list)


if __name__ == '__main__':
    UpdateNodeList.default().run()
