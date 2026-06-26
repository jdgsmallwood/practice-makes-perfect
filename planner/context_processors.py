def planner_session(request):
    if not hasattr(request, "session"):
        return {"planner_current_section": None}
    state = request.session.get("planner_state")
    if not state:
        return {"planner_current_section": None}
    current_section = next(
        (s for s in state["sections"] if s["completed_at"] is None),
        None,
    )
    return {"planner_current_section": current_section}
