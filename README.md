# everyday_tools

##fk2googlecal.py
Parses a pdf exported from Försäkringskassan on parental leave and adds days to your google calendar.

For this to work you need to follow the steps at https://developers.google.com/google-apps/calendar/quickstart/python to enable the API.

Steps that may go wrong:
- If you have the six package installed via pip the quickstart.py script may fail. Try installing via easy_install, then point your pythonpath to the easy_install
default directory.
- For some reason having VLC running at the same time as you run the quickstart.py script to get credentials a popup for VLC stream opens and requests a username and password.
- Installing httplib2 via pip may set the wrong permissions for cacerts.txt, fix this by adding read permission for 'others'.
