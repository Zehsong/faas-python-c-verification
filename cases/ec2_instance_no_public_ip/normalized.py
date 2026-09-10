def faas_model(state_id: int) -> int:
    if state_id < 0 or state_id > 127:
        return -1

    message_type = (state_id // 32) % 4
    config_status = (state_id // 8) % 4
    event_left_scope = (state_id // 4) % 2
    has_public_ip = (state_id // 2) % 2
    test_mode = state_id % 2

    # OTHER message type -> internal error response.
    if message_type == 3:
        return 6

    # ScheduledNotification produces no configuration item.
    # In the source, evaluate_compliance would then dereference None.
    if message_type == 1:
        return 7

    applicable = (
        (config_status == 0 or config_status == 1)
        and event_left_scope == 0
    )

    if not applicable:
        base = 4
    elif has_public_ip:
        base = 2
    else:
        base = 0

    return base + test_mode
