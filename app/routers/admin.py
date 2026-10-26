from fastapi import APIRouter

from ..deps import AdminUser, Conn
from ..schemas import DepartmentEdit, DepartmentIn, PasswordIn, UserCreate, UserEdit
from ..services import admin as service

router = APIRouter(prefix="/admin", tags=["管理"])


@router.get("/departments")
def list_departments(conn: Conn, admin: AdminUser):
    return service.list_departments(conn)


@router.post("/departments", status_code=201)
def create_department(body: DepartmentIn, conn: Conn, admin: AdminUser):
    return {"id": service.create_department(conn, body.name)}


@router.put("/departments/{department_id}", status_code=204)
def update_department(department_id: int, body: DepartmentEdit, conn: Conn, admin: AdminUser):
    """改名、指定经理。"""
    service.update_department(conn, department_id, body)


@router.get("/users")
def list_users(conn: Conn, admin: AdminUser):
    return service.list_users(conn)


@router.post("/users", status_code=201)
def create_user(body: UserCreate, conn: Conn, admin: AdminUser):
    return {"id": service.create_user(conn, admin, body)}


@router.put("/users/{user_id}", status_code=204)
def update_user(user_id: int, body: UserEdit, conn: Conn, admin: AdminUser):
    """改姓名、角色、部门。"""
    service.update_user(conn, admin, user_id, body)


@router.post("/users/{user_id}/deactivate", status_code=204)
def deactivate(user_id: int, conn: Conn, admin: AdminUser):
    service.set_active(conn, admin, user_id, False)


@router.post("/users/{user_id}/activate", status_code=204)
def activate(user_id: int, conn: Conn, admin: AdminUser):
    service.set_active(conn, admin, user_id, True)


@router.post("/users/{user_id}/password", status_code=204)
def reset_password(user_id: int, body: PasswordIn, conn: Conn, admin: AdminUser):
    service.reset_password(conn, user_id, body.password)
