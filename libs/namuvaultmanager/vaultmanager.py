import asyncio
from dataclasses import dataclass
import logging
import sys
import sqlitecloud
import sqlite3
from typing import List, Optional, Any, Dict, Tuple, Type

from libs.utils.list_walker import walk, Child
from libs.utils.ref import Ref, make_temp
from libs.utils.hash import fnv1a_64_signed

class UniversalType():
    _type_map = {
        1: list,
        2: tuple,
        3: set,
        4: dict,
        5: int,
        6: float,
        7: str,
        8: bool,
        9: complex,
        10: bytes,
    }
            
    @staticmethod
    def get_type_int(type: int) -> Type:
        return UniversalType._type_map.get(type)

    @staticmethod
    def get_int(type: Type) -> int:
        if type is list:
            return 1
        elif type is tuple:
            return 2
        elif type is set:
            return 3
        elif type is dict:
            return 4
        elif type is int:
            return 5
        elif type is float:
            return 6
        elif type is str:
            return 7
        elif type is bool:
            return 8
        elif type is complex:
            return 9
        elif type is bytes:
            return 10
        else:
            raise ValueError(f"Unsupported type: {type}")

    @staticmethod
    def is_container(type: int) -> bool:
        if type is not None:
            return type <= 4
        return False

@dataclass
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
            database_item = DatabaseItem(data[0], data[1], data[2], data[3], data[4], data[5], data[6])
            if database_item.value is not None:
                database_item.value = UniversalType.get_type_int(database_item.data_type)(database_item.value)
            if (database_item.key and UniversalType.is_container(database_item.data_type)) or database_item.parent_key:
                process.setdefault(database_item.key or database_item.parent_key, []).append(database_item)
            else:
                dict[database_item.key] = database_item.value

        for key, database_items in tuple(process.items()):
            database_items.sort(key=lambda x: (x.parent_id if x.parent_id is not None else -1, 0 if x.continuous_id is None else 1, 0 if x.parent_key is not None else float('-inf')))
            if database_items[0].key and UniversalType.is_container(database_items[0].data_type):
                construct = make_temp(UniversalType.get_type_int(database_items[0].data_type)())
                database_items.pop(0)
                ref = Ref(construct)
                for database_item in database_items:
                    if database_item.parent_id:
                        ref.id = database_item.parent_id
                    if not UniversalType.is_container(database_item.data_type):
                        ref.append(database_item.value)
                    else:
                        ref.indices_ids[database_item.id] = (pi,)+(len(ref),) if (pi := database_item.parent_id) else (len(ref),)
                        ref.append(UniversalType.get_type_int(database_item.data_type)())
                dict[key] = ref.final()

    def create_table(self, connection, table):
        with connection:
            connection.execute(f"CREATE TABLE IF NOT EXISTS '{table}'(key INTEGER UNIQUE, value, data_type INT, continuous_id INTEGER, id INTEGER, parent_id INTEGER, parent_key INTEGER)")
    def db_get_all(self, connection, table):
        with connection:
            return connection.execute(f"""
                SELECT * FROM '{table}'
            """).fetchall()
    def db_execute_clear(self, connection, table, key):
        with connection:
            connection.execute(f"""
                DELETE FROM '{table}' WHERE key = ? OR parent_key = ?
            """, (key, key))
    def db_walk_execute_store(self, key, connection, table, value):
        execute_data = []
        for depth, value in tuple(walk(value).items()):
            con_id = 0
            last_parent_id = None
            for item in value:
                if last_parent_id != item.parent_id:
                    con_id = -1
                con_id += 1
                last_parent_id = item.parent_id
                if depth == -1:
                    if type(item) is Child:
                        execute_data.append((key, item.value, UniversalType.get_int(iv) if (iv := item.type) is not type(None) else None, None, None, None, None))
                        continue
                    execute_data.append((key, None, UniversalType.get_int(item.type), None, None, None, None))
                    continue
                if type(item) is Child:
                    execute_data.append((None, item.value, UniversalType.get_int(iv) if (iv := item.type) is not type(None) else None, con_id if con_id else None, None, item.parent_id, key))
                    continue
                execute_data.append((None, None, UniversalType.get_int(item.type), con_id if con_id else None, item.id, item.parent_id, key))

        with connection:
            self.db_execute_clear(connection, table, key)
            connection.executemany(f"""
                INSERT INTO '{table}' (key, value, data_type, continuous_id, id, parent_id, parent_key)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, execute_data)

    def db_vault_store(self, connection, table, key: str, value: Any):
        self.create_table(connection, table)
        self.db_walk_execute_store(key, connection, table, value)
        connection.commit()
    async def vault_store(self, vault: 'Vault', key: str, value: Any) -> 'Vault':
        hashed_key = fnv1a_64_signed(key)
        await asyncio.get_running_loop().run_in_executor(None, self.db_vault_store, await self.get_connection(), self.get_table(vault.owner, vault.group), hashed_key, value)
        vault.data[hashed_key] = value

    def db_vault_delete(self, connection, table, key: str):
        self.create_table(connection, table)
        self.db_execute_clear(connection, table, key)
        connection.commit()
    async def vault_delete(self, vault: 'Vault', key: str) -> 'Vault':
        hashed_key = fnv1a_64_signed(key)
        await asyncio.get_running_loop().run_in_executor(None, self.db_vault_delete, await self.get_connection(), self.get_table(vault.owner, vault.group), hashed_key)
        try:
            del vault.data[hashed_key]
        except Exception:
            pass

    def db_vault_get_all(self, connection, table):
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

    async def store(self, key: str, value: Any):
        await self.vault_manager.vault_store(self, key, value)

    async def delete(self, key: str):
        await self.vault_manager.vault_delete(self, key)

    def get(self, key: str) -> Any:
        return self.data.get(fnv1a_64_signed(key))