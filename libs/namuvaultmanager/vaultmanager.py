import asyncio
from dataclasses import dataclass
import logging
import sys
import sqlitecloud
import sqlite3
from enum import Enum
from typing import List, Optional, Any, Dict, Tuple
from pydoc import locate

from libs.utils.list_walker import walk, Child
from libs.utils.ref import Ref, make_temp
from libs.utils.hash import fnv1a_64_signed

class ContinuousType(Enum):
    List = 1
    Tuple = 2
    Set = 3
    Dict = 4

    def get_continuous(type: 'ContinuousType') -> Any:
        match type:
            case ContinuousType.List:
                return list()
            case ContinuousType.Tuple:
                return tuple()
            case ContinuousType.Set:
                return set()
            case ContinuousType.Dict:
                return dict()

    def get_continuous_enum(type: type) -> 'ContinuousType':
        if type is list:
            return ContinuousType.List
        elif type is tuple:
            return ContinuousType.Tuple
        elif type is set:
            return ContinuousType.Set
        elif type is dict:
            return ContinuousType.Dict

@dataclass
class DatabaseItem:
    key: str
    value: Any
    data_type: str
    continuous_type: int
    continuous_id: int
    id: int
    parent_id: int
    parent_key: str

class VaultManager():
    def __init__(self, database: str, is_sqlitecloud: bool = False, logger: Optional[logging.Logger] = None):
        self.logger = logger
        if not logger:
            self.logger: logging.Logger = logging.getLogger('')
            self.logger.setLevel(logging.INFO)
            self.logger.addHandler(logging.StreamHandler(sys.stdout))

        self.is_sqlitecloud = is_sqlitecloud
        self.db_connect_str=database
        self.db=self.connect_db()

        self.vault_pool: Dict[str, Vault] = {}

    def connect_db(self):
        try:
            if self.is_sqlitecloud:
                return sqlitecloud.connect(self.db_connect_str)
            else:
                return sqlite3.connect(self.db_connect_str, check_same_thread=False)
        except Exception as e:
            self.logger.error(f"Failed to connect to Vault Database.. (Reason: {e})") 

    def check_connection(self):
        try:
            cur = self.db.cursor()
            cur.execute("""SELECT 1""")
        except Exception as ex:
            self.logger.info(f"Reconnecting to Vault Database... (Reason: {repr(ex)})")
            self.db = self.connect_db()
            return self.check_connection()
        return self.db
                
    async def get_connection(self):
        return await asyncio.get_running_loop().run_in_executor(None, self.check_connection)

    def get_table(self, owner: str, group: Optional[str] = None):
        return f"{owner}.{group}" if group else owner

    async def populate_dict_from_db_list(self, array: List[Tuple], dict: Dict):
        process = {}
        for data in array:
            database_item = DatabaseItem(data[0], data[1], data[2], data[3], data[4], data[5], data[6], data[7])
            if database_item.data_type and database_item.value:
                database_item.value = locate(database_item.data_type)(database_item.value)
            
            if database_item.key and database_item.continuous_type:
                process.setdefault(database_item.key, []).append(database_item)
            if database_item.parent_key:
                process.setdefault(database_item.parent_key, []).append(database_item)
            elif database_item.key and database_item.value:
                dict[database_item.key] = database_item.value

        for key, value in list(process.items()):
            value.sort(key=lambda x: (x.parent_id if x.parent_id is not None else -1, 0 if x.continuous_id is None else 1, x.continuous_id if x.continuous_id is not None else float('-inf')))
            array_map = {}
            for database_item in value:
                if database_item.key and database_item.continuous_type:
                    dict[key] = make_temp(ContinuousType.get_continuous(ContinuousType(database_item.continuous_type)))
                elif database_item.parent_key:
                    ref = Ref(dict[key], am if (am := array_map.get(database_item.parent_id)) else [])
                    if database_item.continuous_type is None:
                        ref.append(database_item.value)
                    else:
                        array_map[database_item.id] = pi+[len(ref)] if (pi := array_map.get(database_item.parent_id)) else [len(ref)]
                        ref.append(ContinuousType.get_continuous(ContinuousType(database_item.continuous_type)))
            ref = Ref(dict[key])
            dict[key] = ref.final()

    def create_table(self, cursor, table):
        cursor.execute(f"CREATE TABLE IF NOT EXISTS '{table}'(key INTEGER UNIQUE, value, data_type TEXT, continuous_type INTEGER, continuous_id INTEGER, id INTEGER, parent_id INTEGER, parent_key INTEGER)")
    def db_get_all(self, cursor, table):
        return cursor.execute(f"""
            SELECT * FROM '{table}'
            """).fetchall()
    def db_execute_clear(self, cursor, table, key):
        cursor.execute(f"""
            DELETE FROM '{table}' WHERE key = ? OR parent_key = ?
            """, (key, key))
    def db_execute_store(self, cursor, table, key, value, data_type, continuous_type, continuous_id, id, parent_id, parent_key):
        cursor.execute(f"""
            INSERT OR REPLACE INTO '{table}' (key, value, data_type, continuous_type, continuous_id, id, parent_id, parent_key) VALUES
            (?, ?, ?, ?, ?, ?, ?, ?)
            """, (key, value, data_type, continuous_type, continuous_id, id, parent_id, parent_key))
    def db_walk_execute_store(self, key, cursor, table, value):
        self.db_execute_clear(cursor, table, key)
        walked = walk(value)
        sorted_walk = sorted(walked.items())
        sorted_walk.reverse()

        for idx, value in sorted_walk:
            con_id = 0
            last_parent_id = None
            for item in value:
                if last_parent_id != item.parent_id:
                    con_id = -1
                con_id += 1
                last_parent_id = item.parent_id
                if idx == -1:
                    if type(item) is Child:
                        self.db_execute_store(cursor, table, key, item.value, type(item.value).__name__, None, None, None, None, None)
                        continue
                    self.db_execute_store(cursor, table, key, None, None, ContinuousType.get_continuous_enum(item.type).value, None, None, None, None)
                    continue
                if type(item) is Child:
                    self.db_execute_store(cursor, table, None, item.value, type(iv).__name__ if (iv := item.value) is not None else None, None, con_id, None, item.parent_id, key)
                    continue
                self.db_execute_store(cursor, table, None, None, None, ContinuousType.get_continuous_enum(item.type).value, con_id, item.id, item.parent_id, key)

    def db_vault_store(self, connection, table, key: str, value: Any):
        cur = connection.cursor()
        self.create_table(cur, table)
        self.db_walk_execute_store(key, cur, table, value)
        connection.commit()
    async def vault_store(self, vault: 'Vault', key: str, value: Any) -> 'Vault':
        hashed_key = fnv1a_64_signed(key)
        await asyncio.get_running_loop().run_in_executor(None, self.db_vault_store, await self.get_connection(), self.get_table(vault.owner, vault.group), hashed_key, value)
        vault.data[hashed_key] = value

    def db_vault_delete(self, connection, table, key: str):
        cur = connection.cursor()
        self.create_table(cur, table)
        self.db_execute_clear(cur, table, key)
        connection.commit()
    async def vault_delete(self, vault: 'Vault', key: str) -> 'Vault':
        hashed_key = fnv1a_64_signed(key)
        await asyncio.get_running_loop().run_in_executor(None, self.db_vault_delete, await self.get_connection(), self.get_table(vault.owner, vault.group), hashed_key)
        try:
            del vault.data[hashed_key]
        except Exception:
            pass

    def db_vault_get_all(self, connection, table):
        cur = connection.cursor()
        self.create_table(cur, table)
        return self.db_get_all(cur, table)
    async def vault_get_all(self, vault: 'Vault'):
        return await asyncio.get_running_loop().run_in_executor(None, self.db_vault_get_all, await self.get_connection(), self.get_table(vault.owner, vault.group))

    async def get(self, owner: str, group: Optional[str] = None) -> 'Vault':
        table = self.get_table(owner, group)
        if not (vault := self.vault_pool.get(table)):
            vault = Vault(self, owner, group)
            db_list = await self.vault_get_all(vault)
            await self.populate_dict_from_db_list(db_list, vault.data)
            self.vault_pool[table] = vault
        return vault

class Vault():
    def __init__(self, vault_manager: VaultManager, owner: str, group: Optional[str] = None):
        self.vault_manager: VaultManager = vault_manager
        self.owner: str = owner
        self.group: Optional[str] = group
        self.data: Dict[str, Any] = {}

    async def store(self, key: str, value: Any):
        await self.vault_manager.vault_store(self, key, value)

    async def delete(self, key: str):
        await self.vault_manager.vault_delete(self, key)

    def get(self, key: str) -> Any:
        return self.data.get(fnv1a_64_signed(key))