import socket
from contextlib import closing
from datetime import datetime, timedelta
from typing import Iterable, Optional

import requests
from prometheus_client.parser import text_string_to_metric_families


class AptosNode:
    def __init__(self, host: str, update_frequency: timedelta = timedelta(hours=1), api_port: int = 8080,
                 metrics_port: Optional[int] = 9101, seed_port: Optional[int] = 6180, proto: str = 'http') -> None:
        self.__proto = proto
        self.__host = host
        self.__update_frequency: timedelta = update_frequency if update_frequency else timedelta(hours=2)
        self.__api_port = api_port
        self.__metrics_port = metrics_port
        self.__seed_port = seed_port
        self.__last_updated: Optional[datetime] = None
        self.chain_id: Optional[int] = None
        self.epoch: Optional[int] = None
        self.ledger_version: Optional[str] = None
        self.ledger_timestamp: Optional[str] = None
        self.api_port_opened: Optional[bool] = None
        self.metrics_port_opened: Optional[bool] = None
        self.seed_port_opened: Optional[bool] = None
        self.synced: Optional[bool] = None
        self.error: Optional[str] = None
        self.out_of_sync_threshold = 5000

    def __test_port(self, port: Optional[int]) -> bool:
        if port is None:
            return True
        with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
            sock.settimeout(5)
            return sock.connect_ex((self.__host, port)) == 0

    def __update_ledger_version(self):
        if not self.__test_port(self.__api_port):
            return
        info = requests.get(f'{self.__proto}://{self.__host}:{self.__api_port}', timeout=5)
        if info.status_code != 200:
            raise Exception(f"API ledger unavailable")
        info = info.json()
        self.chain_id = '23'  # info["chain_id"] TODO: REPLACE ONCE TESTNET GOES ONLINE
        self.epoch = info["epoch"]
        self.ledger_version = int(info["ledger_version"])
        self.ledger_timestamp = int(info["ledger_timestamp"])

    @staticmethod
    def __first_or_none(iterable: Iterable):
        return next(iter(iterable), None) if iterable else None

    def __update_synced(self):
        if not self.__metrics_port or not self.__test_port(self.__metrics_port):
            return
        metrics = requests.get(f'{self.__proto}://{self.__host}:{self.__metrics_port}/metrics', timeout=5)
        if metrics.status_code != 200:
            raise Exception(f"Node metrics unavailable")
        metrics = list(text_string_to_metric_families(metrics.text))
        sync_metrics = self.__first_or_none(a for a in metrics if a.name == 'aptos_state_sync_version')
        if not sync_metrics:
            raise Exception(f"Sync metrics undefined")
        synced = self.__first_or_none(a for a in sync_metrics.samples if a.labels['type'] == 'synced')
        applied = self.__first_or_none(
            a for a in sync_metrics.samples if a.labels['type'] == 'applied_transaction_outputs')
        self.synced = None if not synced or not applied else abs(
            synced.value - applied.value) < self.out_of_sync_threshold

    def update(self):
        if self.__last_updated and datetime.utcnow() - self.__last_updated <= self.__update_frequency:
            return
        try:
            self.api_port_opened = self.__test_port(self.__api_port)
            self.metrics_port_opened = self.__test_port(self.__metrics_port)
            self.seed_port_opened = self.__test_port(self.__seed_port)
            self.__update_ledger_version()
            self.__update_synced()
            self.__last_updated = datetime.utcnow()
        except Exception as e:
            self.error = e.message
