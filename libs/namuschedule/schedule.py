from typing import ClassVar, Dict, Protocol, Any, Callable, Awaitable
from dataclasses import field
from dataclasses import make_dataclass
from dataclasses import dataclass
from dataclasses import asdict
from datetime import datetime
import time
from threading import Thread
from threading import Event

import sqlite3
import sqlitecloud
import asyncio

from asyncinit import asyncinit

class Dataclass(Protocol):
    __dataclass_fields__: ClassVar[Dict[str, Any]] 

@dataclass
class RowReference:
    table: str
    id: int

@dataclass
class Payload:
    name: str
    trigger_on: datetime
    reference: RowReference
    attrs: dict = field(default_factory=dict)

@asyncinit
class Schedule():
    async def __init__(self, database: str, is_sqlitecloud: bool = False):
        self.is_sqlitecloud = is_sqlitecloud
        self.db_connect_str=database
        self.db=self.connect_db()
        self.subscribers={}

        self.payloads = self.get_all_payloads()
        
        self.loop = asyncio.get_running_loop()
        self.loop_thread = Thread(target = self.start_check_payload_loop)
        self.reset_event = Event()
        self.loop_thread.start()

    def get_all_payloads(self):
        payload_refs = self.__get_payload_refs_db(self.check_connection())
        payloads=[]
        for values in payload_refs:
            payloads.append(Payload(values[1][values[1].find(".")+1:], datetime.fromtimestamp(values[0]), RowReference(*values[1:])))
        return payloads

    def start_check_payload_loop(self):
        while True:
            time.sleep(1)
            if self.payloads:
                target_payload: Payload = self.payloads[0]
                self.reset_event.wait(max(0, target_payload.trigger_on.timestamp()-time.time()))
                if self.reset_event.is_set():
                    self.reset_event.clear()
                    continue
                
                if not target_payload.attrs:
                    target_payload.attrs = self.__get_attrs(self.check_connection(), target_payload.reference)
                decoded_payload=self.decode_payload(target_payload)
                subscribers=self.subscribers.get(target_payload.name)
                if subscribers:
                    for subscriber in subscribers:
                        asyncio.run_coroutine_threadsafe(subscriber(decoded_payload), self.loop)
                self.__delete_payload_db(self.check_connection(), target_payload)
                del self.payloads[0]        

    def subscribe(self, object_name: str, callback: Callable[['Payload'], Awaitable[Any]]):
        if not self.subscribers.get(object_name):
            self.subscribers[object_name] = []
        self.subscribers[object_name].append(callback)

    def connect_db(self):
        try:
            if self.is_sqlitecloud:
                return sqlitecloud.connect(self.db_connect_str)
            else:
                return sqlite3.connect(self.db_connect_str, check_same_thread=False)
        except Exception as e:
            print(f"Failed to connect to Schedule Database.. (Reason: {e})") 

    def check_connection(self):
        try:
            cur = self.db.cursor()
            cur.execute("""SELECT 1""")
        except Exception as ex:
            print(f"Reconnecting to Schedule Database... (Reason: {repr(ex)})")
            self.db = self.connect_db()
            return self.check_connection()
        return self.db
                
    async def get_connection(self):
        self.event_loop = asyncio.get_running_loop()
        return await self.event_loop.run_in_executor(None, self.check_connection)
    
    def __get_attrs(self, connection, row_reference: RowReference):
        cur = connection.cursor()
        values = list(cur.execute(f"""
            SELECT * FROM '{row_reference.table}' WHERE ROWID = ?
        """, (row_reference.id,)).fetchone())
        keys = [description[0] for description in cur.description]
        return dict(zip(keys, values))
    def __delete_payload_db(self, connection, payload: Payload):
        cur = connection.cursor()
        cur.execute("""
            DELETE FROM 'schedule'
            WHERE id = ? AND payload_table = ?""", (payload.reference.id,payload.reference.table))
        cur.execute(f"""
            DELETE FROM '{payload.reference.table}'
            WHERE ROWID = ?""", (payload.reference.id,))
        connection.commit()
    def __get_payload_refs_db(self, connection):
        cur = connection.cursor()
        cur.execute("CREATE TABLE IF NOT EXISTS 'schedule'(trigger, payload_table, id)")
        return cur.execute("""
            SELECT * FROM 'schedule' ORDER BY trigger
        """).fetchall()
    def __add_payload_db(self, connection, table, trigger_on: datetime, object: Dataclass):
        attrs: dict = {}
        name: str = type(object).__name__
        for key, value in asdict(object).items():
            attrs[key]=repr(value)

        payload_keys=tuple(attrs.keys())
        payload_sqlite_values=str(payload_keys).replace("'", "")
        payload_table=f'{table}.{name}'
        cur = connection.cursor()
        cur.execute(f"CREATE TABLE IF NOT EXISTS '{payload_table}'{payload_sqlite_values}")
        cur.execute(f"""
            INSERT INTO '{payload_table}' VALUES
                {"("+("?, "*len(attrs))[:-2]+")"}
            """, tuple(attrs.values()))
        
        row=RowReference(payload_table, cur.lastrowid)
        cur.execute("CREATE TABLE IF NOT EXISTS 'schedule'(trigger, payload_table, id)")
        cur.execute("""
            INSERT INTO 'schedule' VALUES
                (?, ?, ?)
            """, (trigger_on.timestamp(), row.table, row.id))
        connection.commit()
        return Payload(name, trigger_on, row, attrs)
    
    async def add_payload(self, table: str, trigger_on: datetime, object: Dataclass):
        loop=asyncio.get_running_loop()
        payload=await loop.run_in_executor(None, self.__add_payload_db, await self.get_connection(), table, trigger_on, object)
        self.payloads.append(payload)
        self.payloads.sort(key=lambda p: p.trigger_on.timestamp())
        self.reset_event.set()
        return payload

    def decode_payload(self, payload: Payload) -> Dataclass:
        attrs={}
        for key, value in payload.attrs.items():
            attrs[key]=eval(value)
        decoded=make_dataclass(payload.name, attrs)
        return decoded(**attrs)