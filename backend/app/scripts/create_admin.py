"""Create an administrator account.

Administrators cannot self-register through the API. Run from the backend/ directory
with the virtual environment active:

    python -m app.scripts.create_admin --email you@example.com --name "Your Name"

The password is read from the ADMIN_PASSWORD environment variable if set,
otherwise you are prompted for it (input is hidden).
"""

import argparse
import getpass
import os
import sys

from pydantic import ValidationError
from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.enums import UserRole
from app.models.user import User
from app.schemas.user import UserRegister
from app.services.audit import record_audit


def _read_password() -> str:
    from_env = os.environ.get("ADMIN_PASSWORD")
    if from_env:
        return from_env
    first = getpass.getpass("Admin password: ")
    if first != getpass.getpass("Repeat password: "):
        sys.exit("Passwords do not match.")
    return first


def main() -> None:
    parser = argparse.ArgumentParser(description="Create an administrator account.")
    parser.add_argument("--email", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--phone", default=None)
    args = parser.parse_args()

    try:
        # Reuse the registration rules for name, email, phone and password strength.
        data = UserRegister(full_name=args.name, email=args.email, phone=args.phone, password=_read_password())
    except ValidationError as exc:
        for error in exc.errors():
            print(f"- {error['loc'][0]}: {error['msg']}", file=sys.stderr)
        sys.exit(1)

    with SessionLocal() as db:
        if db.scalar(select(User.id).where(User.email == data.email)):
            sys.exit(f"A user with email {data.email} already exists. No changes made.")
        admin = User(
            full_name=data.full_name,
            email=data.email,
            phone=data.phone,
            password_hash=hash_password(data.password),
            role=UserRole.ADMIN,
        )
        db.add(admin)
        db.flush()
        record_audit(db, actor_id=None, action="admin.created_via_cli", entity_type="user", entity_id=admin.id)
        db.commit()
        print(f"Administrator created: {admin.email} (id {admin.id})")


if __name__ == "__main__":
    main()
