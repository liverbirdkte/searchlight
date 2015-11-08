# Copyright (c) 2014 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_log import log as logging
import oslo_messaging
from oslo_utils import encodeutils

from searchlight.elasticsearch.plugins import base
from searchlight.elasticsearch.plugins.glance \
    import serialize_glance_image_members
from searchlight.elasticsearch.plugins.glance \
    import serialize_glance_notification

from searchlight.elasticsearch.plugins.utils import send_notification
LOG = logging.getLogger(__name__)


class ImageHandler(base.NotificationBase):

    def __init__(self, *args, **kwargs):
        super(ImageHandler, self).__init__(*args, **kwargs)
        self.image_delete_keys = ['deleted_at', 'deleted',
                                  'is_public', 'properties']

    def process(self, ctxt, publisher_id, event_type, payload, metadata):
        try:
            actions = {
                "image.create": self.create_or_update,
                "image.update": self.create_or_update,
                "image.delete": self.delete,
                "image.member.create": self.sync_members,
                "image.member.update": self.sync_members,
                "image.member.delete": self.sync_members
            }
            actions[event_type](payload)
            return oslo_messaging.NotificationResult.HANDLED
        except Exception as e:
            LOG.error(encodeutils.exception_to_unicode(e))

    def serialize_notification(self, notification):
        return serialize_glance_notification(notification)

    def create_or_update(self, payload):
        id = payload['id']
        payload = self.serialize_notification(payload)
        self.engine.index(
            index=self.index_name,
            doc_type=self.document_type,
            body=payload,
            id=id
        )
	send_notification(payload)

    def delete(self, payload):
        id = payload['id']
        self.engine.delete(
            index=self.index_name,
            doc_type=self.document_type,
            id=id
        )
	send_notification(payload)

    def sync_members(self, payload):
        image_id = payload['image_id']
        image_es = self.engine.get(
            index=self.index_name,
            doc_type=self.document_type,
            id=image_id
        )
        payload = serialize_glance_image_members(image_es['_source'], payload)
        self.engine.index(
            index=self.index_name,
            doc_type=self.document_type,
            body=payload,
            id=image_id
        )
