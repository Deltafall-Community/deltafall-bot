import asyncio
from dataclasses import dataclass
import logging
import sys
import os
import math
import copy
import sqlitecloud
from typing import List, Optional, Any, Dict, Tuple, Union
import apsw
from concurrent.futures import ThreadPoolExecutor

from libs.utils.list_walker import walk, Child
from libs.utils.ref import Ref, make_temp
from libs.utils.hash import fnv1a_64_signed
from libs.utils.universaltype import UniversalType

MAX_WORKERS = min(32, os.cpu_count() + 4)

# ! --------------- !
# while this class was built with multi-threading in mind
# it is faster to use this class with python 3.14 without GIL
# ! --------------- !

@dataclass(slots=True)
class DatabaseItem:
    key: str
    value: Any
    data_type: int
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
        self.db.execute("PRAGMA journal_mode=WAL")

        self.vault_pool: Dict[str, Vault] = {}

    def connect_db(self):
        try:
            if self.is_sqlitecloud:
                return sqlitecloud.connect(self.db_connect_str)
            else:
                return apsw.Connection(self.db_connect_str)
        except Exception as e:
            self.logger.error(f"Failed to connect to Vault Database.. (Reason: {e})") 

    def check_connection(self):
        try:
            with self.db as connection:
                connection.execute("""SELECT 1""")
        except Exception as ex:
            self.logger.info(f"Reconnecting to Vault Database... (Reason: {repr(ex)})")
            self.db = self.connect_db()
            return self.check_connection()
        return self.db
                
    async def get_connection(self):
        return await asyncio.get_running_loop().run_in_executor(None, self.check_connection)

    def get_table(self, owner: str, group: Optional[str] = None):
        return f"{owner}.{group}" if group else str(owner)

    async def populate_dict_from_db_list(self, array: List[Tuple], dict: Dict):
        loop = asyncio.get_running_loop()
        
        get_type_int = UniversalType.get_type_int
        is_container = UniversalType.is_container
        DatabaseItem_ = DatabaseItem

        def process_chunk(array_chunk):
            local_process = {}
            local_dict = {}
            
            for data in array_chunk:
                database_item = DatabaseItem_(*data)
                if database_item.value is not None:
                    database_item.value = get_type_int(database_item.data_type)(database_item.value)

                if (database_item.key and is_container(database_item.data_type)) or database_item.parent_key:            
                    dk = database_item.key or database_item.parent_key
                    if dk in local_process:
                        local_process[dk].append(database_item)
                    else:
                        local_process[dk] = [database_item]
                else:
                    local_dict[database_item.key] = database_item.value
            return local_process, local_dict

        process = {}

        if array:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                chunk_size = math.ceil(len(array) / MAX_WORKERS)
                chunks = [array[i:i+chunk_size] for i in range(0, len(array), chunk_size)]
                tasks = [loop.run_in_executor(executor, process_chunk, chunk) for chunk in chunks]
                results = await asyncio.gather(*tasks)

            for local_process, local_dict in results:
                dict.update(local_dict)
                for k, v in local_process.items():
                    if k in process:
                        process[k].extend(v)
                    else:
                        process[k] = v

        def process_item(key, database_items):
            database_items.sort(key=lambda x: (x.parent_id if x.parent_id is not None else -1, 0 if x.continuous_id is None else 1, 0 if x.parent_key is not None else float('-inf')))
            if database_items[0].key and is_container(database_items[0].data_type):
                construct = make_temp(get_type_int(database_items[0].data_type))
                database_items.pop(0)
                ref = Ref(construct)
                for database_item in database_items:
                    if database_item.parent_id:
                        ref.id = database_item.parent_id
                    if not is_container(database_item.data_type):
                        ref.append(database_item.value)
                    else:
                        ref.indices_ids[database_item.id] = (pi,)+(len(ref),) if (pi := database_item.parent_id) else (len(ref),)
                        ref.append(get_type_int(database_item.data_type))
                return key, ref.final()
            return key, None
        
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            tasks = [loop.run_in_executor(executor, process_item, key, items) for key, items in process.items()]
            for coro in asyncio.as_completed(tasks):
                key, final_value = await coro
                if final_value is not None:
                    dict[key] = final_value

    def create_table(self, connection, table):
        connection.execute(f"CREATE TABLE IF NOT EXISTS '{table}'(key INTEGER UNIQUE, value, data_type INT, continuous_id INTEGER, id INTEGER, parent_id INTEGER, parent_key INTEGER)")
    def db_get_all(self, connection, table):
        return connection.execute(f"""
            SELECT * FROM '{table}'
        """).fetchall()
    def db_execute_delete(self, connection, table, key):
        connection.execute(f"""
            DELETE FROM '{table}' WHERE key = ? OR parent_key = ?
        """, (key, key))
    def db_execute_clear(self, connection, table):
        connection.execute(f"""
            DROP TABLE IF EXISTS '{table}';
        """)
    
    @staticmethod
    async def walk_execute_data(key, value):
        execute_data = []
        for depth, value in (await walk(value)).items():
            con_id = 0
            last_parent_id = None
            for item in value:
                if last_parent_id != item.parent_id:
                    con_id = -1
                con_id += 1
                last_parent_id = item.parent_id
                current_con_id = con_id if con_id else None
                item_type_int = UniversalType.get_int(item.type)
                is_child = type(item) is Child
                if depth == -1:
                    if is_child:
                        execute_data.append((key, item.value, item_type_int, None, None, None, None))
                    else:
                        execute_data.append((key, None, item_type_int, None, None, None, None))
                else:
                    if is_child:
                        execute_data.append((None, item.value, item_type_int, current_con_id, None, item.parent_id, key))
                    else:
                        execute_data.append((None, None, item_type_int, current_con_id, item.id, item.parent_id, key))
        return execute_data

    def db_vault_store(self, connection, table, keys: List[tuple], execute_data: List[tuple]):
        with connection:
            self.create_table(connection, table)
            connection.executemany(f"""
                DELETE FROM '{table}' WHERE key = ? OR parent_key = ?
            """, keys)
            connection.executemany(f"""
                INSERT INTO '{table}' (key, value, data_type, continuous_id, id, parent_id, parent_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, execute_data)
    async def vault_store(self, vault: 'Vault', key: Union[str, dict], value: Optional[Any] = None) -> 'Vault':
        execute_datas = []
        keys = []
        is_dict = type(key) is dict

        if is_dict:
            for key, value in key.items():
                hashed_key = fnv1a_64_signed(key)
                if not (hashed_key in vault.data and vault.data[hashed_key] == value):
                    keys.append((hashed_key, hashed_key))
                    execute_datas.extend(await self.walk_execute_data(hashed_key, value))
                    vault.data[hashed_key] = value
        else:
            hashed_key = fnv1a_64_signed(key)
            if not (hashed_key in vault.data and vault.data[hashed_key] == value):
                keys.append((hashed_key, hashed_key))
                execute_datas.extend(await self.walk_execute_data(hashed_key, value))
                vault.data[hashed_key] = value
    
        if execute_datas:
            await asyncio.get_running_loop().run_in_executor(None, self.db_vault_store, await self.get_connection(), self.get_table(vault.owner, vault.group), keys, execute_datas)
    

    def db_vault_delete(self, connection, table, key: str):
        with connection:
            self.create_table(connection, table)
            self.db_execute_delete(connection, table, key)
    async def vault_delete(self, vault: 'Vault', key: str) -> 'Vault':
        hashed_key = fnv1a_64_signed(key)
        await asyncio.get_running_loop().run_in_executor(None, self.db_vault_delete, await self.get_connection(), self.get_table(vault.owner, vault.group), hashed_key)
        try:
            del vault.data[hashed_key]
        except Exception:
            pass

    def db_vault_clear(self, connection, table):
        with connection:
            self.db_execute_clear(connection, table)
    async def vault_clear(self, vault: 'Vault') -> 'Vault':
        await asyncio.get_running_loop().run_in_executor(None, self.db_vault_clear, await self.get_connection(), self.get_table(vault.owner, vault.group))
        vault.data.clear()

    def db_vault_get_all(self, connection, table):
        with connection:
            self.create_table(connection, table)
            return self.db_get_all(connection, table)
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

    async def store(self, key: Union[str, dict], value: Optional[Any] = None):
        await self.vault_manager.vault_store(self, key, value)

    async def delete(self, key: str):
        await self.vault_manager.vault_delete(self, key)

    async def clear(self):
        await self.vault_manager.vault_clear(self)

    def get(self, key: str, default: Any = None) -> Any:
        value = copy.copy(self.data.get(fnv1a_64_signed(key)))
        if value is None and default is not None:
            return default
        return value