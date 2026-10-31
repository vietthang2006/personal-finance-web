from uuid import UUID

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, GoalServiceDep
from app.schemas.goal import (
    GoalContributeResponse,
    GoalContributionCreate,
    GoalContributionRead,
    GoalCreate,
    GoalDetailRead,
    GoalRead,
    GoalUpdate,
)

router = APIRouter(prefix="/goals", tags=["goals"])


@router.post("", response_model=GoalRead, status_code=status.HTTP_201_CREATED)
def create_goal(
    payload: GoalCreate,
    user: CurrentUser,
    service: GoalServiceDep,
) -> GoalRead:
    """Creates a new active savings goal for the current user."""
    goal = service.create_goal(user, payload)
    return GoalRead.model_validate(goal)


@router.get("", response_model=list[GoalRead])
def list_goals(
    user: CurrentUser,
    service: GoalServiceDep,
    status_filter: str | None = Query(default=None, alias="status"),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=100),
) -> list[GoalRead]:
    """Lists savings goals for the current user, optionally filtered by status."""
    goals = service.list_goals(
        user_id=user.id,
        status_filter=status_filter,
        offset=offset,
        limit=limit,
    )
    return [GoalRead.model_validate(g) for g in goals]


@router.get("/{goal_id}", response_model=GoalDetailRead)
def get_goal(
    goal_id: UUID,
    user: CurrentUser,
    service: GoalServiceDep,
) -> GoalDetailRead:
    """Retrieves detailed information for a savings goal along with its contribution history."""
    goal, contributions = service.get_goal_detail(user.id, goal_id)
    contrib_reads = [GoalContributionRead.model_validate(c) for c in contributions]
    detail = GoalDetailRead.model_validate(goal)
    detail.contributions = contrib_reads
    return detail


@router.patch("/{goal_id}", response_model=GoalRead)
def update_goal(
    goal_id: UUID,
    payload: GoalUpdate,
    user: CurrentUser,
    service: GoalServiceDep,
) -> GoalRead:
    """Updates savings goal details."""
    goal = service.update_goal(user, goal_id, payload)
    return GoalRead.model_validate(goal)


@router.post("/{goal_id}/cancel", response_model=GoalRead)
def cancel_goal(
    goal_id: UUID,
    user: CurrentUser,
    service: GoalServiceDep,
) -> GoalRead:
    """Cancels an active savings goal."""
    goal = service.cancel_goal(user, goal_id)
    return GoalRead.model_validate(goal)


@router.post(
    "/{goal_id}/contributions",
    response_model=GoalContributeResponse,
    status_code=status.HTTP_201_CREATED,
)
def contribute(
    goal_id: UUID,
    payload: GoalContributionCreate,
    user: CurrentUser,
    service: GoalServiceDep,
) -> GoalContributeResponse:
    """Contributes funds from a user account to a savings goal (Core Workflow W11)."""
    return service.contribute(user, goal_id, payload)
