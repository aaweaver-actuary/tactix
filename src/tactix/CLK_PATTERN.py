"""Regex for clock comment parsing."""

# pylint: disable=invalid-name

import re

CLK_PATTERN = re.compile(r"%clk\s+([0-9:.]+)")
