int faas_model(int state_id)
{
    if (state_id < 0 || state_id > 127)
        return -1;

    int message_type = (state_id / 32) % 4;
    int config_status = (state_id / 8) % 4;
    int event_left_scope = (state_id / 4) % 2;
    int has_public_ip = (state_id / 2) % 2;
    int test_mode = state_id % 2;

    if (message_type == 3)
        return 6;

    if (message_type == 1)
        return 7;

    int applicable =
        (config_status == 0)
        && event_left_scope == 0;

    int base;

    if (!applicable)
        base = 4;
    else if (has_public_ip)
        base = 2;
    else
        base = 0;

    return base + test_mode;
}
