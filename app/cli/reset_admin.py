# app/cli/reset_admin.py
"""CLI tool to reset admin password."""

import asyncio

from sqlalchemy import select

from app.auth.password import generate_password, hash_password
from app.db.models.user import User
from app.db.session import get_async_session


async def reset_admin_password():
    """Reset admin password with confirmation."""
    print("⚠️  This will reset the admin password")
    confirm = input("Continue? (yes/no): ")

    if confirm.lower() != "yes":
        print("Cancelled")
        return

    async with get_async_session() as session:
        stmt = select(User).where(User.username == "admin")
        result = await session.execute(stmt)
        admin = result.scalar_one_or_none()

        if not admin:
            print("❌ Admin user not found")
            return

        new_password = generate_password(16)
        admin.password_hash = hash_password(new_password)
        admin.failed_login_count = 0
        admin.is_active = True

        await session.commit()

        print("✅ Admin password reset")
        print(f"   New password: {new_password}")


if __name__ == "__main__":
    asyncio.run(reset_admin_password())
