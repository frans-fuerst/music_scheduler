#!/usr/bin/env python3
# -*- coding: utf-8 -*-

class rrp_error(Exception):
    pass

class invalid_value(rrp_error):
    pass

class bad_request(rrp_error):
    pass

