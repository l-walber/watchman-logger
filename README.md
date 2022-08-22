# watchman-logger
Converts an incoming xml report file to individual calls and logs them via SMTP.
No further development is going to happen here, this is just being uploaded for posterity/reference.
No support offered either.

To use: create an empty xml folder for the downloaded files, copy the oohconfig_template.py file to oohconfig.py and populate the required details.

One email account to receive the reports, ideally used only for that purpose. An email account to receive the calls and log them.

This requires POP and SMTP access to work (written in the old days before MFA and mandatory use of Exchange).
Schedule the script to run shortly after the report usually arrives. It can be run again a couple of hours later if the report is sometimes delayed.

Obviously this also requires something on the other end to catch the emails and make them into calls - we used to use SupportWorks with autologging rules, but anything similar will work.

If we still used this:
* The SMTP part would be stripped out and replaced with something using the new ITSM tool's API.
* Use of the API would also allow us to log the calls directly under the given user's details without manual intervention (or spoofing shenanigans).
* The POP part would be replaced with IMAP, and maybe bundled into the primary call receiving account since we'd no longer have to download every single email.
* Other minor changes that come with an extra five years worth of programming experience.
