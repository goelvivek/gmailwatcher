# Strings to be used in UI.

from gettext import gettext as _
from gi.repository import GLib


# String constants
icon_name = 'gmailwatcher'

# Messages Tuple of (Title, Description)
no_account = (
        _("Add an account"),
        _("Hey %s, I don't have any accounts to watch over right now."
           "Please add a gmail or google apps account and I'll let you"
           "know about any new emails.") % GLib.get_user_name()
        )

quit = (
        _("ZZZzzzz..."),
        _("If you need me again, you can find me by clicking"
          "he messaging icon in the top panel.")
        )

start = (
        _("Now watching!"),
        _("I'm now watching out for new mail and will stay hidden"
          "until you need me. To summon me, click the messaging icon"
          "in the panel and then click me.")
        )

new_mail = (_("New Mail"), _("%d new emails in %s"))