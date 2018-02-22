#!/usr/bin/env python3

# Copyright 2018 Lionheart Software LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import hashlib
import logging
import re
import urllib.error
import urllib.request
from . import exceptions

looks_like_sha1_re = re.compile(r"^[a-fA-F0-9]{40}")

class PwnedPasswordsAPI(object):
    @staticmethod
    def url(*components, **kwargs):
        value = "https://api.pwnedpasswords.com/" + "/".join(components)
        if len(kwargs) > 0:
            value += "?" + urllib.parse.urlencode(kwargs)

        print(value)
        return value

    @staticmethod
    def request(path, value, **kwargs):
        url = PwnedPasswordsAPI.url(path, value, **kwargs)
        request = urllib.request.Request(
            url=url,
            headers={
                'User-Agent': f"pwnedpasswords (Python)"
            }
        )
        try:
            with urllib.request.urlopen(request) as f:
                response = f.read()
        except urllib.error.HTTPError as e:
            Exception = exceptions.STATUS_CODES_TO_EXCEPTIONS.get(e.code)
            if Exception is not None:
                raise Exception(e.url, e.code, e.msg, e.hdrs, e.fp)

            raise
        else:
            return response.decode("utf-8-sig")

def convert_password_tuple(value):
    hash, count = value.split(":")
    return (hash, int(count))

class Password(object):
    def __init__(self, value, original_password_is_hash=False):
        self.original_password_is_hash = original_password_is_hash

        if looks_like_sha1_re.match(value):
            self.value = value
        else:
            # The provided value is plaintext, so let's hash it. If you'd like
            # to search the provided value as-is, specify `raw=True` in the
            # initializer.
            self.value = hashlib.sha1(value.encode("utf8")).hexdigest()

    def check(self, anonymous=True):
        if anonymous and not self.original_password_is_hash:
            entries = self.range()
            entry = entries.get(self.value[5:].upper())
            if entry is None:
                return 0
            else:
                return entry
        else:
            return self.search()

    def search(self):
        try:
            kwargs = {}
            if self.original_password_is_hash:
                kwargs['originalPasswordIsAHash'] = "true"

            response = PwnedPasswordsAPI.request("pwnedpassword", self.value, **kwargs)
        except exceptions.PasswordNotFound:
            return 0
        else:
            count = int(response)
            return count

    def range(self):
        response = PwnedPasswordsAPI.request("range", self.value[:5])
        entries = dict(map(convert_password_tuple, response.upper().split("\r\n")))
        return entries
