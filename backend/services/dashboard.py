from fastapi import HTTPException, status
from beanie import PydanticObjectId
from database.models.dashboard import Dashboard, GetUserDashboardResponse


class DashboardService:
    async def get_user_dashboard(self, user_id: str) -> GetUserDashboardResponse:
        # Make sure the ID is valid
        try:
            user_object_id = PydanticObjectId(user_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid user ID format."
            )

        # Find the dashboard with linked owner
        dashboard = await Dashboard.find_one({"owner.$id": user_object_id})

        if not dashboard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Dashboard not found for this user."
            )

        # Optional: fetch linked user data if you need full owner info
        await dashboard.owner.fetch()

        return GetUserDashboardResponse(
            id=str(dashboard.id),
            owner=str(dashboard.owner.ref.id),  # Use .ref.id to access the ID
            created_at=dashboard.created_at
        )