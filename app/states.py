"""
States module.
Defines conversation states for multi-step interactions.
"""

# ==================== Account Management States ====================
(
    STATE_ADD_ACCOUNT_NAME,
    STATE_ADD_ACCOUNT_KEY_ID,
    STATE_ADD_ACCOUNT_KEY_SECRET,
    STATE_ADD_ACCOUNT_NOTES,
    STATE_DELETE_ACCOUNT_CONFIRM,
) = range(5)

# ==================== Action States ====================
(
    STATE_RESET_PASSWORD_INPUT,
    STATE_RESET_PASSWORD_CONFIRM,
    STATE_DELETE_INSTANCE_CONFIRM,
    STATE_REINSTALL_IMAGE_ID,
    STATE_REINSTALL_PASSWORD,
    STATE_REINSTALL_CONFIRM,
    STATE_OPEN_TCP_CONFIRM,
    STATE_OPEN_UDP_CONFIRM,
    STATE_OPEN_ALL_CONFIRM,
    STATE_REVOKE_CONFIRM,
) = range(100, 110)

# ==================== Callback Data Prefixes ====================
# Used to route callback queries to the correct handler

CB_MAIN_MENU = "main_menu"
CB_ACCOUNTS_LIST = "accounts_list"
CB_ACCOUNT_SELECT = "acc_sel:"          # acc_sel:<account_id>
CB_ACCOUNT_DELETE = "acc_del:"          # acc_del:<account_id>
CB_ACCOUNT_DELETE_YES = "acc_del_yes:"  # acc_del_yes:<account_id>
CB_ACCOUNT_ADD = "account_add"

CB_REGIONS_SCAN = "regions_scan"
CB_REGION_SELECT = "reg_sel:"           # reg_sel:<region_id>

CB_INSTANCES_LIST = "instances_list"
CB_INSTANCE_SELECT = "inst_sel:"        # inst_sel:<instance_id>
CB_INSTANCE_REFRESH = "inst_refresh:"   # inst_refresh:<instance_id>

# Action callbacks
CB_ACTION_REBOOT = "act_reboot:"        # act_reboot:<instance_id>
CB_ACTION_START = "act_start:"          # act_start:<instance_id>
CB_ACTION_STOP = "act_stop:"            # act_stop:<instance_id>
CB_ACTION_DELETE = "act_delete:"        # act_delete:<instance_id>
CB_ACTION_RESET_PWD = "act_resetpwd:"   # act_resetpwd:<instance_id>
CB_ACTION_REINSTALL = "act_reinstall:"  # act_reinstall:<instance_id>

# Security group callbacks
CB_SG_OPEN_TCP = "sg_tcp:"             # sg_tcp:<instance_id>
CB_SG_OPEN_UDP = "sg_udp:"             # sg_udp:<instance_id>
CB_SG_OPEN_ALL = "sg_all:"             # sg_all:<instance_id>
CB_SG_REVOKE_TCP = "sg_rev_tcp:"       # sg_rev_tcp:<instance_id>
CB_SG_REVOKE_UDP = "sg_rev_udp:"       # sg_rev_udp:<instance_id>
CB_SG_REVOKE_ALL = "sg_rev_all:"       # sg_rev_all:<instance_id>

# Confirmation callbacks
CB_CONFIRM_REBOOT = "cfm_reboot:"      # cfm_reboot:<instance_id>
CB_CONFIRM_STOP = "cfm_stop:"          # cfm_stop:<instance_id>
CB_CONFIRM_START = "cfm_start:"        # cfm_start:<instance_id>
CB_CONFIRM_SG_TCP = "cfm_sg_tcp:"      # cfm_sg_tcp:<instance_id>
CB_CONFIRM_SG_UDP = "cfm_sg_udp:"      # cfm_sg_udp:<instance_id>
CB_CONFIRM_SG_ALL = "cfm_sg_all:"      # cfm_sg_all:<instance_id>
CB_CONFIRM_REV_TCP = "cfm_rev_tcp:"    # cfm_rev_tcp:<instance_id>
CB_CONFIRM_REV_UDP = "cfm_rev_udp:"    # cfm_rev_udp:<instance_id>
CB_CONFIRM_REV_ALL = "cfm_rev_all:"    # cfm_rev_all:<instance_id>

# Navigation
CB_BACK = "back"
CB_HOME = "home"
CB_LOGS = "logs"
CB_HELP = "help"
CB_CANCEL = "cancel"
CB_NOOP = "noop"
