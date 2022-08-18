# oohconfig

CONFIG = {"popserver": "outlook.office365.com",
          "smtpname": "smtp.outlook.office365.com",
          "smtpport": 587,
          "username": "username@example.invalid",  # mailbox to receive out of hours reports
          "user": "outofhours@example.invalid",  # friendly name of this mailbox
          "password": "hunter2",  # password for this mailbox
          "recp": "servicedesk@example.invalid",  # target for the mailbox that will be logging the calls
          "debug": False,
          "debugemail": "operator@example.invalid",  # send emails here instead for debugging
          "logsize": 200000,
          "logbackups": 3}

TEMPLATE = """*** Logged by Out of Hours Support - $res ***
User: $user

$problem

Initial Contact Time : $time
Watchman call reference number : $ref"""
