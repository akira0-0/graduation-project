# -*- coding: utf-8 -*-
"""
规则管理器
负责规则的CRUD操作、版本管理、批量导入导出
"""
import json
import sqlite3
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager

from .models import Rule, RuleCreate, RuleUpdate, RuleVersion


class RuleManager:
    """规则管理器"""
    
    def __init__(self, db_path: str):
        """
        初始化规则管理器
        
        Args:
            db_path: SQLite数据库路径
        """
        self.db_path = Path(db_path)
        self._ensure_db()
    
    @contextmanager
    def _get_conn(self):
        """获取数据库连接"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()
    
    def _ensure_db(self):
        """确保数据库和表存在"""
        schema_path = self.db_path.parent / "schema.sql"
        
        with self._get_conn() as conn:
            if schema_path.exists():
                # 只执行建表语句，忽略已存在的表
                schema = schema_path.read_text(encoding='utf-8')
                for statement in schema.split(';'):
                    statement = statement.strip()
                    if statement and not statement.startswith('--'):
                        try:
                            conn.execute(statement)
                        except sqlite3.OperationalError:
                            pass  # 表已存在
            else:
                # 内联建表
                conn.executescript("""
                    CREATE TABLE IF NOT EXISTS rules (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        type TEXT NOT NULL,
                        content TEXT NOT NULL,
                        category TEXT,
                        priority INTEGER DEFAULT 0,
                        enabled INTEGER DEFAULT 1,
                        description TEXT,
                        version INTEGER DEFAULT 1,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                    
                    CREATE TABLE IF NOT EXISTS rule_versions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        rule_id INTEGER NOT NULL,
                        version INTEGER NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (rule_id) REFERENCES rules(id) ON DELETE CASCADE
                    );
                    
                    CREATE INDEX IF NOT EXISTS idx_rules_enabled ON rules(enabled);
                    CREATE INDEX IF NOT EXISTS idx_rules_category ON rules(category);
                """)
            
            # 数据库迁移：确保新列存在
            self._migrate_db(conn)
    
    def _migrate_db(self, conn):
        """数据库迁移：添加缺失的列"""
        # 获取当前表结构
        cursor = conn.execute("PRAGMA table_info(rules)")
        columns = {row[1] for row in cursor.fetchall()}
        
        # 添加缺失的 description 列
        if 'description' not in columns:
            try:
                conn.execute("ALTER TABLE rules ADD COLUMN description TEXT")
            except sqlite3.OperationalError:
                pass  # 列已存在
        
        # 添加缺失的 purpose 列（默认为 filter）
        if 'purpose' not in columns:
            try:
                conn.execute("ALTER TABLE rules ADD COLUMN purpose TEXT DEFAULT 'filter'")
                # 更新所有现有规则的 purpose 为 filter
                conn.execute("UPDATE rules SET purpose = 'filter' WHERE purpose IS NULL")
            except sqlite3.OperationalError:
                pass  # 列已存在
    
    def _row_to_rule(self, row) -> Rule:
        """将数据库行转换为Rule对象"""
        # 将sqlite3.Row转换为字典以便安全访问
        row_dict = dict(row)
        return Rule(
            id=row_dict['id'],
            name=row_dict['name'],
            type=row_dict['type'],
            content=row_dict['content'],
            category=row_dict.get('category'),
            purpose=row_dict.get('purpose', 'filter'),
            priority=row_dict['priority'],
            enabled=bool(row_dict['enabled']),
            description=row_dict.get('description'),
            version=row_dict['version'],
            created_at=datetime.fromisoformat(row_dict['created_at']) if row_dict.get('created_at') else datetime.now(),
            updated_at=datetime.fromisoformat(row_dict['updated_at']) if row_dict.get('updated_at') else datetime.now(),
        )
    
    # ==================== CRUD操作 ====================
    
    def create(self, data: RuleCreate) -> Rule:
        """创建规则"""
        with self._get_conn() as conn:
            cursor = conn.execute(
                """
                INSERT INTO rules (name, type, content, category, purpose, priority, enabled, description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    data.name,
                    data.type.value if hasattr(data.type, 'value') else data.type,
                    data.content,
                    data.category.value if data.category and hasattr(data.category, 'value') else data.category,
                    data.purpose.value if hasattr(data.purpose, 'value') else (data.purpose or 'filter'),
                    data.priority,
                    1 if data.enabled else 0,
                    data.description,
                )
            )
            rule_id = cursor.lastrowid
            
            # 创建初始版本记录
            conn.execute(
                "INSERT INTO rule_versions (rule_id, version, content) VALUES (?, 1, ?)",
                (rule_id, data.content)
            )
            
            # 获取创建的规则
            row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
            return self._row_to_rule(row)
    
    def get(self, rule_id: int) -> Optional[Rule]:
        """获取单条规则"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM rules WHERE id = ?", (rule_id,)).fetchone()
            return self._row_to_rule(row) if row else None
    
    def get_by_name(self, name: str) -> Optional[Rule]:
        """按名称获取规则"""
        with self._get_conn() as conn:
            row = conn.execute("SELECT * FROM rules WHERE name = ?", (name,)).fetchone()
            return self._row_to_rule(row) if row else None
    
    def list(
        self,
        enabled_only: bool = False,
        category: Optional[str] = None,
        rule_type: Optional[str] = None,
        purpose: Optional[str] = None,
        name_prefix: Optional[str] = None,
        limit: int = 1000,
        offset: int = 0,
    ) -> List[Rule]:
        """获取规则列表
        
        Args:
            enabled_only: 只返回启用的规则
            category: 按分类筛选
            rule_type: 按类型筛选
            purpose: 按用途筛选 (filter/select)
            name_prefix: 按规则名称前缀筛选，如 "通用-" 只取通用场景规则
            limit: 返回数量限制
            offset: 偏移量
        """
        query = "SELECT * FROM rules WHERE 1=1"
        params = []
        
        if enabled_only:
            query += " AND enabled = 1"
        if category:
            query += " AND category = ?"
            params.append(category)
        if rule_type:
            query += " AND type = ?"
            params.append(rule_type)
        if purpose:
            query += " AND purpose = ?"
            params.append(purpose)
        if name_prefix:
            query += " AND name LIKE ?"
            params.append(name_prefix + "%")
        
        query += " ORDER BY priority DESC, id ASC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        with self._get_conn() as conn:
            rows = conn.execute(query, params).fetchall()
            return [self._row_to_rule(row) for row in rows]
    
    def update(self, rule_id: int, data: RuleUpdate) -> Optional[Rule]:
        """更新规则"""
        rule = self.get(rule_id)
        if not rule:
            return None
        
        # 构建更新字段
        updates = []
        params = []
        
        for field, value in data.model_dump(exclude_unset=True).items():
            if value is not None:
                if hasattr(value, 'value'):  # Enum
                    value = value.value
                updates.append(f"{field} = ?")
                params.append(value)
        
        if not updates:
            return rule
        
        # 如果content变更，需要增加版本
        new_version = rule.version
        if data.content is not None and data.content != rule.content:
            new_version = rule.version + 1
            updates.append("version = ?")
            params.append(new_version)
        
        updates.append("updated_at = ?")
        params.append(datetime.now().isoformat())
        params.append(rule_id)
        
        with self._get_conn() as conn:
            conn.execute(
                f"UPDATE rules SET {', '.join(updates)} WHERE id = ?",
                params
            )
            
            # 如果content变更，记录版本
            if data.content is not None and data.content != rule.content:
                conn.execute(
                    "INSERT INTO rule_versions (rule_id, version, content) VALUES (?, ?, ?)",
                    (rule_id, new_version, data.content)
                )
        
        return self.get(rule_id)
    
    def delete(self, rule_id: int) -> bool:
        """删除规则"""
        with self._get_conn() as conn:
            cursor = conn.execute("DELETE FROM rules WHERE id = ?", (rule_id,))
            return cursor.rowcount > 0
    
    def toggle(self, rule_id: int) -> Optional[Rule]:
        """切换规则启用状态"""
        with self._get_conn() as conn:
            conn.execute(
                "UPDATE rules SET enabled = NOT enabled, updated_at = ? WHERE id = ?",
                (datetime.now().isoformat(), rule_id)
            )
        return self.get(rule_id)
    
    # ==================== 版本管理 ====================
    
    def get_versions(self, rule_id: int) -> List[RuleVersion]:
        """获取规则的版本历史"""
        with self._get_conn() as conn:
            rows = conn.execute(
                "SELECT * FROM rule_versions WHERE rule_id = ? ORDER BY version DESC",
                (rule_id,)
            ).fetchall()
            return [
                RuleVersion(
                    id=row['id'],
                    rule_id=row['rule_id'],
                    version=row['version'],
                    content=row['content'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
                )
                for row in rows
            ]
    
    def rollback(self, rule_id: int, version: int) -> Optional[Rule]:
        """回滚到指定版本"""
        with self._get_conn() as conn:
            row = conn.execute(
                "SELECT content FROM rule_versions WHERE rule_id = ? AND version = ?",
                (rule_id, version)
            ).fetchone()
            
            if not row:
                return None
            
            # 获取当前版本
            rule = self.get(rule_id)
            if not rule:
                return None
            
            new_version = rule.version + 1
            
            conn.execute(
                "UPDATE rules SET content = ?, version = ?, updated_at = ? WHERE id = ?",
                (row['content'], new_version, datetime.now().isoformat(), rule_id)
            )
            
            # 记录新版本
            conn.execute(
                "INSERT INTO rule_versions (rule_id, version, content) VALUES (?, ?, ?)",
                (rule_id, new_version, row['content'])
            )
        
        return self.get(rule_id)
    
    # ==================== 批量操作 ====================
    
    def export_rules(self, rule_ids: Optional[List[int]] = None) -> List[Dict[str, Any]]:
        """导出规则"""
        if rule_ids:
            rules = [self.get(rid) for rid in rule_ids]
            rules = [r for r in rules if r is not None]
        else:
            rules = self.list()
        
        return [
            {
                "name": r.name,
                "type": r.type,
                "content": r.content,
                "category": r.category,
                "priority": r.priority,
                "enabled": r.enabled,
                "description": r.description,
            }
            for r in rules
        ]
    
    def import_rules(
        self,
        rules_data: List[Dict[str, Any]],
        overwrite: bool = False,
    ) -> Dict[str, int]:
        """
        批量导入规则
        
        Returns:
            {"created": 数量, "updated": 数量, "skipped": 数量}
        """
        result = {"created": 0, "updated": 0, "skipped": 0}
        
        for data in rules_data:
            existing = self.get_by_name(data.get("name", ""))
            
            if existing:
                if overwrite:
                    self.update(existing.id, RuleUpdate(**data))
                    result["updated"] += 1
                else:
                    result["skipped"] += 1
            else:
                try:
                    self.create(RuleCreate(**data))
                    result["created"] += 1
                except Exception:
                    result["skipped"] += 1
        
        return result
    
    # ==================== 统计 ====================
    
    def count(self, enabled_only: bool = False) -> int:
        """统计规则数量"""
        query = "SELECT COUNT(*) FROM rules"
        if enabled_only:
            query += " WHERE enabled = 1"
        
        with self._get_conn() as conn:
            return conn.execute(query).fetchone()[0]
    
    def stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._get_conn() as conn:
            total = conn.execute("SELECT COUNT(*) FROM rules").fetchone()[0]
            enabled = conn.execute("SELECT COUNT(*) FROM rules WHERE enabled = 1").fetchone()[0]
            
            # 按类型统计
            type_stats = {}
            for row in conn.execute("SELECT type, COUNT(*) as cnt FROM rules GROUP BY type"):
                type_stats[row['type']] = row['cnt']
            
            # 按分类统计
            category_stats = {}
            for row in conn.execute("SELECT category, COUNT(*) as cnt FROM rules WHERE category IS NOT NULL GROUP BY category"):
                category_stats[row['category']] = row['cnt']
            
            return {
                "total": total,
                "enabled": enabled,
                "disabled": total - enabled,
                "by_type": type_stats,
                "by_category": category_stats,
            }
