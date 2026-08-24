"""
models/audit_model.py
----------------------
Handles administrative audit logging (Phase 5).
"""

import json
from models.db import mysql

def log_admin_action(admin_id, action, target_type, target_id=None, details=None):
    """
    Logs an administrative action to the database.
    :param admin_id: ID of the admin performing the action.
    :param action: Action string (e.g., 'ADD_BOOK', 'DELETE_USER').
    :param target_type: Entity type (e.g., 'BOOK', 'USER').
    :param target_id: ID of the affected entity.
    :param details: Dictionary of changes or additional info.
    """
    try:
        details_json = json.dumps(details) if details else None
        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO admin_audit_logs (admin_id, action, target_type, target_id, details)
            VALUES (%s, %s, %s, %s, %s)
        """, (admin_id, action, target_type, target_id, details_json))
        mysql.connection.commit()
        cur.close()
        return True
    except Exception as e:
        print(f"Error logging admin action: {e}")
        return False

def get_audit_logs(admin_id=None, action=None, limit=50, offset=0):
    """
    Retrieves audit logs with optional filters.
    """
    where = []
    params = []
    if admin_id:
        where.append("a.admin_id = %s")
        params.append(admin_id)
    if action:
        where.append("a.action = %s")
        params.append(action)
    
    where_sql = " WHERE " + " AND ".join(where) if where else ""
    
    cur = mysql.connection.cursor()
    cur.execute(f"""
        SELECT a.*, u.name as admin_name, u.username as admin_username
        FROM admin_audit_logs a
        JOIN users u ON a.admin_id = u.user_id
        {where_sql}
        ORDER BY a.timestamp DESC
        LIMIT %s OFFSET %s
    """, params + [limit, offset])
    
    logs = cur.fetchall()
    cur.close()
    return logs
