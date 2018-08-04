# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
#  Purpose: Mattermost driver.
#   Author: Tom Parker
#
# -----------------------------------------------------------------------------
"""
tomputils.mattermost
====================

A simple Mattermost driver.

:license:
    CC0 1.0 Universal
    http://creativecommons.org/publicdomain/zero/1.0/
"""

from .mattermost import Mattermost, format_timedelta, format_span

__all__ = ['format_timedelta', 'format_span', 'Mattermost']
