# Copyright 2015 Hewlett-Packard Corporation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from six.moves.urllib.request import Request, urlopen
import json

def normalize_date_fields(document,
                          created_at='created',
                          updated_at='updated'):
    """Attempt to normalize documents to make it easier for consumers,
    particularly around sorting.
    """
    if created_at and 'created_at' not in document:
        document[u'created_at'] = document[created_at]
    if updated_at and 'updated_at' not in document:
        document[u'updated_at'] = document[updated_at]

def send_notification(message):
    push_url = 'http://localhost:8888/v2/queues/testqueue/messages'
    data = {'messages':[
             {'ttl':1000,
             'body': message}]}
    header = {'Client-ID': '133c9b5c-7ed0-11e5-83e0-4335d873a583',
              'X-Project-Id': 'demo',
              'Content-Type': 'application/json'
             }
    req = Request(push_url, json.dumps(data), header)
    rep = urlopen(req).read()
    print rep

