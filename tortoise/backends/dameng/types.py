from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Dict

# Dameng database keywords and reserved words
DM_KEYWORDS = {
    # A
    'ABORT', 'ABSOLUTE', 'ABSTRACT', 'ACCESSED', 'ACCOUNT', 'ACROSS', 'ACTION', 'ADD', 'ADMIN', 
    'ADVANCED', 'AFTER', 'AGGREGATE', 'ALL', 'ALLOW_DATETIME', 'ALLOW_IP', 'ALTER', 'ANALYZE', 
    'AND', 'ANY', 'APPLY', 'APR', 'ARCHIVE', 'ARCHIVEDIR', 'ARCHIVELOG', 'ARCHIVESTYLE', 'ARRAY', 
    'ARRAYLEN', 'AS', 'ASC', 'ASCII', 'ASENSITIVE', 'ASSIGN', 'ASYNCHRONOUS', 'AT', 'ATTACH', 
    'AUDIT', 'AUG', 'AUTHID', 'AUTHORIZATION', 'AUTO', 'AUTO_INCREMENT', 'AUTOEXTEND', 
    'AUTONOMOUS_TRANSACTION', 'AVG',
    
    # B
    'BACKED', 'BACKUP', 'BACKUPDIR', 'BACKUPINFO', 'BACKUPSET', 'BADFILE', 'BAKFILE', 'BASE', 
    'BATCH', 'BEFORE', 'BEGIN', 'BETWEEN', 'BIGDATEDIFF', 'BIGINT', 'BINARY', 'BIT', 'BITMAP', 
    'BLOB', 'BLOCK', 'BOOL', 'BOOLEAN', 'BOTH', 'BRANCH', 'BREADTH', 'BREAK', 'BSTRING', 'BTREE', 
    'BUFFER', 'BUILD', 'BULK', 'BY', 'BYDAY', 'BYHOUR', 'BYMINUTE', 'BYMONTH', 'BYMONTHDAY', 
    'BYSECOND', 'BYTE', 'BYWEEKNO', 'BYYEARDAY',
    
    # C
    'CACHE', 'CALCULATE', 'CALL', 'CASCADE', 'CASCADED', 'CASE', 'CASE_SENSITIVE', 'CAST', 
    'CATALOG', 'CATCH', 'CHAIN', 'CHANGE', 'CHAR', 'CHARACTER', 'CHARACTERISTICS', 'CHECK', 
    'CHECKPOINT', 'CIPHER', 'CLASS', 'CLOB', 'CLOSE', 'CLUSTER', 'CLUSTERBTR', 'COLLATE', 
    'COLLATION', 'COLLECT', 'COLUMN', 'COLUMNS', 'COMMENT', 'COMMIT', 'COMMITTED', 'COMMITWORK', 
    'COMPILE', 'COMPLETE', 'COMPRESS', 'COMPRESSED', 'CONDITIONAL', 'CONNECT', 
    'CONNECT_BY_ISCYCLE', 'CONNECT_BY_ISLEAF', 'CONNECT_BY_ROOT', 'CONNECT_IDLE_TIME', 
    'CONNECT_TIME', 'CONST', 'CONSTANT', 'CONSTRAINT', 'CONSTRAINTS', 'CONSTRUCTOR', 'CONTAINS', 
    'CONTEXT', 'CONTINUE', 'CONVERT', 'COPY', 'CORRESPONDING', 'CORRUPT', 'COUNT', 'COUNTER', 
    'CPU_PER_CALL', 'CPU_PER_SESSION', 'CREATE', 'CROSS', 'CRYPTO', 'CTLFILE', 'CUBE', 
    'CUMULATIVE', 'CURRENT', 'CURRENT_SCHEMA', 'CURRENT_USER', 'CURSOR', 'CYCLE',
    
    # D
    'DAILY', 'DANGLING', 'DATA', 'DATABASE', 'DATAFILE', 'DATE', 'DATEADD', 'DATEDIFF', 
    'DATEPART', 'DATETIME', 'DAY', 'DBFILE', 'DDL', 'DDL_CLONE', 'DEBUG', 'DEC', 'DECIMAL', 
    'DECLARE', 'DECODE', 'DEFAULT', 'DEFERRABLE', 'DEFERRED', 'DEFINER', 'DELETE', 'DELETING', 
    'DELIMITED', 'DELTA', 'DEMAND', 'DENSE_RANK', 'DEPTH', 'DEREF', 'DESC', 'DETACH', 
    'DETERMINISTIC', 'DEVICE', 'DIAGNOSTICS', 'DICTIONARY', 'DIRECTORY', 'DISABLE', 'DISCONNECT', 
    'DISKGROUP', 'DISKSPACE', 'DISTINCT', 'DISTRIBUTED', 'DML', 'DO', 'DOMAIN', 'DOUBLE', 'DOWN', 
    'DROP', 'DUMP',
    
    # E
    'EACH', 'EDITIONABLE', 'ELSE', 'ELSEIF', 'ELSIF', 'EMPTY', 'ENABLE', 'ENCRYPT', 'ENCRYPTION', 
    'END', 'EQU', 'ERROR', 'ERRORS', 'ESCAPE', 'EVALNAME', 'EVENTINFO', 'EVENTS', 'EXCEPT', 
    'EXCEPTION', 'EXCEPTION_INIT', 'EXCEPTIONS', 'EXCHANGE', 'EXCLUDE', 'EXCLUDING', 'EXCLUSIVE', 
    'EXEC', 'EXECUTE', 'EXISTS', 'EXIT', 'EXPIRE', 'EXPLAIN', 'EXTENDS', 'EXTERN', 'EXTERNAL', 
    'EXTERNALLY', 'EXTRACT',
    
    # F
    'FAILED_LOGIN_ATTEMPS', 'FAILED_LOGIN_ATTEMPTS', 'FAST', 'FEB', 'FETCH', 'FIELDS', 'FILE', 
    'FILEGROUP', 'FILESIZE', 'FILLFACTOR', 'FINAL', 'FINALLY', 'FIRST', 'FLASHBACK', 'FLOAT', 
    'FOLLOWS', 'FOLLOWING', 'FOR', 'FORALL', 'FORCE', 'FOREIGN', 'FORMAT', 'FREQ', 'FREQUENCE', 
    'FRI', 'FROM', 'FULL', 'FULLY', 'FUNCTION',
    
    # G
    'GENERATED', 'GET', 'GLOBAL', 'GLOBALLY', 'GLOBAL_SESSION_PER_USER', 'GOTO', 'GRANT', 
    'GREAT', 'GROUP', 'GROUPING',
    
    # H
    'HASH', 'HASHPARTMAP', 'HAVING', 'HEXTORAW', 'HIGH', 'HOLD', 'HOUR', 'HOURLY', 'HUGE',
    
    # I
    'IDENTIFIED', 'IDENTIFIER', 'IDENTITY', 'IDENTITY_INSERT', 'IF', 'IFNULL', 
    'IGNORE_ROW_ON_DUPKEY_INDEX', 'IMAGE', 'IMMEDIATE', 'IN', 'INCLUDE', 'INCLUDING', 'INCREASE', 
    'INCREMENT', 'INDEX', 'INDEXES', 'INDICES', 'INITIAL', 'INITIALIZED', 'INITIALLY', 'INLINE', 
    'INNER', 'INNERID', 'INPUT', 'INSENSITIVE', 'INSERT', 'INSERTING', 'INSTANCE', 'INSTANTIABLE', 
    'INSTEAD', 'INT', 'INTEGER', 'INTENT', 'INTERSECT', 'INTERVAL', 'INTO', 'INVISIBLE', 'IS', 
    'ISOLATION', 'INACTIVE_ACCOUNT_TIME',
    
    # J-Z
    'JAN', 'JAVA', 'JOB', 'JOIN', 'JSON', 'JSON_TABLE', 'JUL', 'JUN',
    'KEEP', 'KEY', 'KEYS',
    'LABEL', 'LARGE', 'LAST', 'LAX', 'LEADING', 'LEFT', 'LEFTARG', 'LESS', 'LEVEL', 'LEVELS', 
    'LEXER', 'LIKE', 'LIMIT', 'LINK', 'LIST', 'LNNVL', 'LOB', 'LOCAL', 'LOCAL_OBJECT', 'LOCALLY', 
    'LOCATION', 'LOCK', 'LOCKED', 'LOG', 'LOGFILE', 'LOGGING', 'LOGIN', 'LOGOFF', 'LOGON', 
    'LOGOUT', 'LONG', 'LONGVARBINARY', 'LONGVARCHAR', 'LOOP', 'LSN',
    'MANUAL', 'MAP', 'MAPPED', 'MAR', 'MATCH', 'MATCHED', 'MATERIALIZED', 'MAX', 
    'MAX_RUN_DURATION', 'MAXPIECESIZE', 'MAXSIZE', 'MAXVALUE', 'MAY', 'MEM_SPACE', 'MEMBER', 
    'MEMORY', 'MERGE', 'MICRO', 'MIN', 'MINEXTENTS', 'MINUS', 'MINUTE', 'MINUTELY', 'MINVALUE', 
    'MIRROR', 'MOD', 'MODE', 'MODIFY', 'MON', 'MONEY', 'MONITORING', 'MONTH', 'MONTHLY', 'MOUNT', 
    'MOVE', 'MOVEMENT', 'MULTISET',
    'NATIONAL', 'NATURAL', 'NCHAR', 'NCHARACTER', 'NEVER', 'NEW', 'NEXT', 'NO', 'NOARCHIVELOG', 
    'NOAUDIT', 'NOBRANCH', 'NOCACHE', 'NOCOPY', 'NOCYCLE', 'NODE', 'NOLOGGING', 'NOMAXVALUE', 
    'NOMINVALUE', 'NOMONITORING', 'NONE', 'NONEDITIONABLE', 'NOORDER', 'NOPARALLEL', 'NORMAL', 
    'NOROWDEPENDENCIES', 'NOSORT', 'NOT', 'NOT_ALLOW_DATETIME', 'NOT_ALLOW_IP', 'NOV', 
    'NOVALIDATE', 'NOWAIT', 'NULL', 'NULLS', 'NUMBER', 'NUMERIC',
    'OBJECT', 'OCT', 'OF', 'OFF', 'OFFLINE', 'OFFSET', 'OIDINDEX', 'OLD', 'ON', 'ONCE', 'ONLINE', 
    'ONLY', 'OPEN', 'OPERATOR', 'OPTIMIZE', 'OPTION', 'OR', 'ORDER', 'ORDINALITY', 'OUT', 'OUTER', 
    'OVER', 'OVERLAPS', 'OVERLAY', 'OVERRIDE', 'OVERRIDING',
    'PACKAGE', 'PAD', 'PAGE', 'PARALLEL', 'PARALLEL_ENABLE', 'PARMS', 'PARTIAL', 'PARTITION', 
    'PARTITIONS', 'PASSING', 'PASSWORD', 'PASSWORD_GRACE_TIME', 'PASSWORD_LIFE_TIME', 
    'PASSWORD_LOCK_TIME', 'PASSWORD_POLICY', 'PASSWORD_REUSE_MAX', 'PASSWORD_REUSE_TIME', 'PATH', 
    'PENDANT', 'PERCENT', 'PIPE', 'PIPELINED', 'PIVOT', 'PLACING', 'PLS_INTEGER', 'PRAGMA', 
    'PREBUILT', 'PRECEDES', 'PRECEDING', 'PRECISION', 'PRESERVE', 'PRETTY', 'PRIMARY', 'PRINT', 
    'PRIOR', 'PRIVATE', 'PRIVILEGE', 'PRIVILEGES', 'PROCEDURE', 'PROFILE', 'PROTECTED', 'PUBLIC', 
    'PURGE',
    'QUERY_REWRITE_INTEGRITY', 'QUOTA',
    'RAISE', 'RANDOMLY', 'RANGE', 'RAWTOHEX', 'READ', 'READ_PER_CALL', 'READ_PER_SESSION', 
    'READONLY', 'REAL', 'REBUILD', 'RECORD', 'RECORDS', 'REDUCED', 'REF', 'REFERENCE', 
    'REFERENCES', 'REFERENCING', 'REFRESH', 'REJECT', 'RELATED', 'RELATIVE', 'RELEASE', 'RENAME', 
    'REPEAT', 'REPEATABLE', 'REPLACE', 'REPLAY', 'REPLICATE', 'RESIZE', 'RESTORE', 'RESTRICT', 
    'RESTRICT_REFERENCES', 'RESULT', 'RESULT_CACHE', 'RETURN', 'RETURNING', 'REVERSE', 'REVOKE', 
    'RIGHT', 'RIGHTARG', 'ROLE', 'ROLLBACK', 'ROLLFILE', 'ROLLUP', 'ROOT', 'ROW', 'ROWCOUNT', 
    'ROWDEPENDENCIES', 'ROWID', 'ROWNUM', 'ROWS', 'RULE',
    'SALT', 'SAMPLE', 'SAT', 'SAVE', 'SAVEPOINT', 'SBYTE', 'SCHEMA', 'SCHEMABINDING', 'SCN', 
    'SCOPE', 'SCROLL', 'SEALED', 'SEARCH', 'SECOND', 'SECONDLY', 'SECTION', 'SEED', 'SELECT', 
    'SELF', 'SENSITIVE', 'SEP', 'SEQUENCE', 'SERERR', 'SERIALIZABLE', 'SERVER', 'SESSION', 
    'SESSION_PER_USER', 'SET', 'SETS', 'SHADOW', 'SHARE', 'SHORT', 'SHUTDOWN', 'SIBLINGS', 
    'SIMPLE', 'SINCE', 'SIZE', 'SIZEOF', 'SKIP', 'SMALLINT', 'SNAPSHOT', 'SOME', 'SOUND', 'SPACE', 
    'SPAN', 'SPATIAL', 'SPEED', 'SPFILE', 'SPLIT', 'SQL', 'STANDBY', 'STARTUP', 'STAT', 
    'STATEMENT', 'STATIC', 'STDDEV', 'STOP', 'STORAGE', 'STORE', 'STRICT', 'STRING', 'STRIPING', 
    'STRUCT', 'STYLE', 'SUBPARTITION', 'SUBPARTITIONS', 'SUBSCRIBE', 'SUBSTITUTABLE', 'SUBSTRING', 
    'SUBTYPE', 'SUCCESSFUL', 'SUM', 'SUN', 'SUSPEND', 'SWITCH', 'SYNC', 'SYNCHRONOUS', 'SYNONYM', 
    'SYS_CONNECT_BY_PATH', 'SYSTEM',
    'TABLE', 'TABLESPACE', 'TASK', 'TEMPLATE', 'TEMPORARY', 'TEXT', 'THAN', 'THEN', 'THREAD', 
    'THROUGH', 'THROW', 'THU', 'TIES', 'TIME', 'TIME_ZONE', 'TIMER', 'TIMES', 'TIMESTAMP', 
    'TIMESTAMPADD', 'TIMESTAMPDIFF', 'TINYINT', 'TO', 'TOP', 'TRACE', 'TRACKING', 'TRAILING', 
    'TRANSACTION', 'TRANSACTIONAL', 'TRIGGER', 'TRIGGERS', 'TRIM', 'TRUNCATE', 'TRUNCSIZE', 
    'TRXID', 'TRY', 'TUE', 'TYPE', 'TYPEDEF', 'TYPEOF',
    'UINT', 'ULONG', 'UNBOUNDED', 'UNCOMMITTED', 'UNCONDITIONAL', 'UNDER', 'UNION', 'UNIQUE', 
    'UNLIMITED', 'UNLOCK', 'UNPIVOT', 'UNTIL', 'UNUSABLE', 'UP', 'UPDATE', 'UPDATING', 'USAGE', 
    'USE_HASH', 'USE_MERGE', 'USE_NL', 'USE_NL_WITH_INDEX', 'USER', 'USHORT', 'USING',
    'VALUE', 'VALUES', 'VALIDATE', 'VARBINARY', 'VARCHAR', 'VARCHAR2', 'VARIANCE', 'VARRAY', 
    'VARYING', 'VERIFY', 'VERSIONS', 'VERSIONS_ENDTIME', 'VERSIONS_ENDTRXID', 'VERSIONS_OPERATION', 
    'VERSIONS_STARTTIME', 'VERSIONS_STARTTRXID', 'VERTICAL', 'VIEW', 'VIRTUAL', 'VISIBLE', 'VOID', 
    'VSIZE',
    'WAIT', 'WED', 'WEEK', 'WEEKLY', 'WHEN', 'WHENEVER', 'WHERE', 'WHILE', 'WITH', 'WITHIN', 
    'WITHOUT', 'WORK', 'WRAPPED', 'WRAPPER', 'WRITE',
    'XML', 'XMLAGG', 'XMLATTRIBUTES', 'XMLELEMENT', 'XMLPARSE', 'XMLTABLE', 'XMLNAMESPACES', 
    'XMLSERIALIZE',
    'YEAR', 'YEARLY',
    'ZONE',
}


# Dameng database type to Tortoise ORM field type mapping
DM_TO_TORTOISE_FIELD_MAP: Dict[str, str] = {
    # String types
    'CHAR': 'CharField',
    'CHARACTER': 'CharField',
    'VARCHAR': 'CharField',
    'VARCHAR2': 'CharField',
    'ROWID': 'CharField',
    'TEXT': 'TextField',
    'LONG': 'TextField',
    'LONGVARCHAR': 'TextField',
    'CLOB': 'TextField',
    # Integer types
    'TINYINT': 'SmallIntField',
    'BYTE': 'SmallIntField',
    'SMALLINT': 'SmallIntField',
    'INTEGER': 'IntField',
    'INT': 'IntField',
    'BIGINT': 'BigIntField',
    # Float types
    'FLOAT': 'FloatField',
    'REAL': 'FloatField',
    'DOUBLE': 'FloatField',
    'DOUBLE PRECISION': 'FloatField',
    # Decimal types
    'NUMERIC': 'DecimalField',
    'DECIMAL': 'DecimalField',
    'DEC': 'DecimalField',
    'NUMBER': 'DecimalField',
    # Binary types
    'BINARY': 'BinaryField',
    'VARBINARY': 'BinaryField',
    'RAW': 'BinaryField',
    'IMAGE': 'BinaryField',
    'LONGVARBINARY': 'BinaryField',
    'BLOB': 'BinaryField',
    'BFILE': 'CharField',  # Stores file path
    # Date/time types
    'DATE': 'DateField',
    'TIME': 'TimeField',
    'TIMESTAMP': 'DatetimeField',
    'DATETIME': 'DatetimeField',
    'TIME WITH TIME ZONE': 'TimeField',
    'TIMESTAMP WITH TIME ZONE': 'DatetimeField',
    'DATETIME WITH TIME ZONE': 'DatetimeField',
    'TIMESTAMP WITH LOCAL TIME ZONE': 'DatetimeField',
    'DATETIME WITH LOCAL TIME ZONE': 'DatetimeField',
    # Interval types
    'INTERVAL YEAR TO MONTH': 'CharField',
    'INTERVAL YEAR': 'CharField',
    'INTERVAL MONTH': 'CharField',
    'INTERVAL DAY': 'TimeDeltaField',
    'INTERVAL DAY TO HOUR': 'TimeDeltaField',
    'INTERVAL DAY TO MINUTE': 'TimeDeltaField',
    'INTERVAL DAY TO SECOND': 'TimeDeltaField',
    'INTERVAL HOUR': 'TimeDeltaField',
    'INTERVAL HOUR TO MINUTE': 'TimeDeltaField',
    'INTERVAL HOUR TO SECOND': 'TimeDeltaField',
    'INTERVAL MINUTE': 'TimeDeltaField',
    'INTERVAL MINUTE TO SECOND': 'TimeDeltaField',
    'INTERVAL SECOND': 'TimeDeltaField',
    # Other types
    'BIT': 'BooleanField',
}


# Tortoise ORM field type to Dameng database type mapping
TORTOISE_TO_DM_FIELD_MAP: Dict[str, str] = {
    'BigIntField': 'BIGINT',
    'BinaryField': 'BLOB',
    'BooleanField': 'BIT',
    'CharField': 'VARCHAR',
    'DateField': 'DATE',
    'DatetimeField': 'TIMESTAMP',
    'DecimalField': 'DECIMAL',
    'FloatField': 'DOUBLE',
    'IntField': 'INT',
    'JSONField': 'CLOB',
    'SmallIntField': 'SMALLINT',
    'TextField': 'CLOB',
    'TimeField': 'TIME',
    'TimeDeltaField': 'BIGINT',  # Store as milliseconds
    'UUIDField': 'VARCHAR(36)',
}


# Data type conversion functions
def dm_type_to_python(dm_type: str, value: Any) -> Any:
    """Convert Dameng database value to Python type.
    
    Args:
        dm_type: Dameng database field type
        value: Database returned value
        
    Returns:
        Converted Python value
    """
    if value is None:
        return None
    
    dm_type = dm_type.upper()
    
    # String types
    if dm_type in (
        'CHAR', 'CHARACTER', 'VARCHAR', 'VARCHAR2', 'ROWID', 
        'TEXT', 'LONG', 'LONGVARCHAR', 'CLOB'
    ):
        return str(value)
    
    # Integer types
    elif dm_type in ('TINYINT', 'BYTE', 'SMALLINT', 'INTEGER', 'INT', 'BIGINT'):
        return int(value)
    
    # Float types
    elif dm_type in ('FLOAT', 'REAL', 'DOUBLE', 'DOUBLE PRECISION'):
        return float(value)
    
    # Decimal types
    elif dm_type in ('NUMERIC', 'DECIMAL', 'DEC', 'NUMBER'):
        return Decimal(str(value))
    
    # Boolean type
    elif dm_type == 'BIT':
        return bool(value)
    
    # Binary types
    elif dm_type in (
        'BINARY', 'VARBINARY', 'RAW', 'IMAGE', 'LONGVARBINARY', 'BLOB'
    ):
        return bytes(value) if not isinstance(value, bytes) else value
    
    # Date/time types
    elif dm_type == 'DATE':
        if isinstance(value, datetime.date):
            return value
        elif isinstance(value, datetime.datetime):
            return value.date()
        else:
            return datetime.datetime.strptime(str(value), '%Y-%m-%d').date()
    
    elif dm_type == 'TIME' or dm_type == 'TIME WITH TIME ZONE':
        if isinstance(value, datetime.time):
            return value
        elif isinstance(value, datetime.datetime):
            return value.time()
        else:
            return datetime.datetime.strptime(str(value), '%H:%M:%S').time()
    
    elif dm_type in (
        'TIMESTAMP', 'DATETIME', 'TIMESTAMP WITH TIME ZONE', 
        'DATETIME WITH TIME ZONE', 'TIMESTAMP WITH LOCAL TIME ZONE', 
        'DATETIME WITH LOCAL TIME ZONE'
    ):
        if isinstance(value, datetime.datetime):
            return value
        else:
            return datetime.datetime.strptime(str(value), '%Y-%m-%d %H:%M:%S')
    
    # Interval types
    elif dm_type.startswith('INTERVAL'):
        # Return string representation, application layer needs further processing
        return str(value)
    
    # BFILE - file path
    elif dm_type == 'BFILE':
        return str(value)
    
    # Default return original value
    return value


def python_to_dm_type(python_value: Any, dm_type: str) -> Any:
    """Convert Python type to Dameng database acceptable value.
    
    Args:
        python_value: Python value
        dm_type: Target Dameng database type
        
    Returns:
        Converted database value
    """
    if python_value is None:
        return None
    
    dm_type = dm_type.upper()
    
    # String types
    if dm_type in (
        'CHAR', 'CHARACTER', 'VARCHAR', 'VARCHAR2', 'ROWID', 
        'TEXT', 'LONG', 'LONGVARCHAR', 'CLOB', 'BFILE'
    ):
        return str(python_value)
    
    # Integer types
    elif dm_type in ('TINYINT', 'BYTE', 'SMALLINT', 'INTEGER', 'INT', 'BIGINT'):
        return int(python_value)
    
    # Float types
    elif dm_type in ('FLOAT', 'REAL', 'DOUBLE', 'DOUBLE PRECISION'):
        return float(python_value)
    
    # Decimal types
    elif dm_type in ('NUMERIC', 'DECIMAL', 'DEC', 'NUMBER'):
        if isinstance(python_value, Decimal):
            return python_value
        else:
            return Decimal(str(python_value))
    
    # Boolean type
    elif dm_type == 'BIT':
        return 1 if python_value else 0
    
    # Binary types
    elif dm_type in (
        'BINARY', 'VARBINARY', 'RAW', 'IMAGE', 'LONGVARBINARY', 'BLOB'
    ):
        if isinstance(python_value, bytes):
            return python_value
        else:
            return bytes(python_value, 'utf-8') if isinstance(python_value, str) else bytes(python_value)
    
    # Date types
    elif dm_type == 'DATE':
        if isinstance(python_value, datetime.date):
            return python_value
        elif isinstance(python_value, datetime.datetime):
            return python_value.date()
    
    # Time types
    elif dm_type in ('TIME', 'TIME WITH TIME ZONE'):
        if isinstance(python_value, datetime.time):
            return python_value
        elif isinstance(python_value, datetime.datetime):
            return python_value.time()
    
    # Timestamp types
    elif dm_type in (
        'TIMESTAMP', 'DATETIME', 'TIMESTAMP WITH TIME ZONE', 
        'DATETIME WITH TIME ZONE', 'TIMESTAMP WITH LOCAL TIME ZONE', 
        'DATETIME WITH LOCAL TIME ZONE'
    ):
        if isinstance(python_value, datetime.datetime):
            return python_value
        elif isinstance(python_value, datetime.date):
            return datetime.datetime.combine(python_value, datetime.time())
    
    # Interval types - TimeDelta to seconds or days
    elif dm_type.startswith('INTERVAL'):
        if isinstance(python_value, datetime.timedelta):
            if 'DAY' in dm_type:
                return python_value.days
            elif 'HOUR' in dm_type or 'MINUTE' in dm_type or 'SECOND' in dm_type:
                return int(python_value.total_seconds())
            else:
                return str(python_value)
        return str(python_value)
    
    # Default return original value
    return python_value


def is_dm_keyword(identifier: str) -> bool:
    """Check if identifier is a Dameng database keyword or reserved word.
    
    Args:
        identifier: Identifier to check
        
    Returns:
        True if keyword, False otherwise
    """
    return identifier.upper() in DM_KEYWORDS


def quote_identifier(identifier: str) -> str:
    """Quote identifier, add double quotes if keyword or contains special characters.
    
    Args:
        identifier: Identifier to quote
        
    Returns:
        Quoted identifier
    """
    # Dameng database uses double quotes for identifiers
    if is_dm_keyword(identifier) or not identifier.isidentifier():
        return f'"{identifier.upper()}"'
    return f'"{identifier.upper()}"'  # Dameng identifiers are uppercase by default


# Data type length and precision mapping
DM_TYPE_LENGTH_MAP: Dict[str, Dict[str, Any]] = {
    # String types
    'CHAR': {'max_length': 32767, 'default_length': 1},
    'VARCHAR': {'max_length': 32767, 'default_length': 255},
    'VARCHAR2': {'max_length': 32767, 'default_length': 255},
    # Numeric types
    'DECIMAL': {'max_precision': 38, 'max_scale': 127, 'default_precision': 10, 'default_scale': 2},
    'NUMERIC': {'max_precision': 38, 'max_scale': 127, 'default_precision': 10, 'default_scale': 2},
    'NUMBER': {'max_precision': 38, 'max_scale': 127, 'default_precision': 10, 'default_scale': 2},
    # Binary types
    'BINARY': {'max_length': 32767, 'default_length': 1},
    'VARBINARY': {'max_length': 32767, 'default_length': 255},
    'RAW': {'max_length': 32767, 'default_length': 255},
}


def get_field_sql_with_params(field_type: str, field_obj: Any) -> str:
    """Generate SQL type definition with parameters based on field object.
    
    Args:
        field_type: Tortoise ORM field type
        field_obj: Field object
        
    Returns:
        SQL type definition string
    """
    base_type = TORTOISE_TO_DM_FIELD_MAP.get(field_type, 'VARCHAR')
    
    # Handle types that need length parameters
    if field_type == 'CharField' and hasattr(field_obj, 'max_length'):
        return f"VARCHAR({field_obj.max_length})"
    
    elif field_type == 'DecimalField':
        max_digits = getattr(field_obj, 'max_digits', 10)
        decimal_places = getattr(field_obj, 'decimal_places', 2)
        return f"DECIMAL({max_digits},{decimal_places})"
    
    elif field_type == 'BinaryField' and hasattr(field_obj, 'max_length'):
        return f"VARBINARY({field_obj.max_length})"
    
    return base_type