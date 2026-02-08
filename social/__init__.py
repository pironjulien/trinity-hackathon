"""
SOCIAL: Trinity's Communication Channels
═══════════════════════════════════════════════════════════════════════════════
External interfaces for communication. Trinity and Jobs can connect here.

Channels:
- messaging/ : Notification Client (messaging)
- web/      : WebApp interface (browser)
- android/  : Mobile app (future)
- cli/      : Command line interface

Architecture:
- Trinity → social/channels → users
- Jobs → social/channels → users
"""

# Unified exports (future: unified channel interface)
__all__ = ["messaging", "web", "android", "cli"]
