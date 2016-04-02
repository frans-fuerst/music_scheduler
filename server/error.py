#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class rrp_error(Exception):
    id_str = "base_error"

class internal_error(rrp_error):
    id_str = "internal_error"

class invalid_value(rrp_error):
    id_str = "invalid_value"

class invalid_state(rrp_error):
    id_str = "invalid_state"

class bad_request(rrp_error):
    id_str = "bad_request"

class not_identified(rrp_error):
    id_str = "not_identified"
