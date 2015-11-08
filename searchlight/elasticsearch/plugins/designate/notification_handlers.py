# Copyright 2015 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from elasticsearch import exceptions
from elasticsearch import helpers
from oslo_log import log as logging
import oslo_messaging

from searchlight.elasticsearch.plugins import base
from searchlight.elasticsearch.plugins import designate


LOG = logging.getLogger(__name__)


class DomainHandler(base.NotificationBase):
    def __init__(self, *args, **kwargs):
        super(DomainHandler, self).__init__(*args, **kwargs)
        self.domain_delete_keys = ['deleted_at', 'deleted',
                                   'attributes', 'recordsets']

    def _serialize(self, payload):
        for key in self.domain_delete_keys:
            if key in payload:
                del payload[key]

        if 'masters' in payload:
            payload['masters'] = ["%(host)s:%(port)s" for i in
                                  payload["masters"]]
        payload['project_id'] = payload.pop('tenant_id')
        if not payload['updated_at'] and payload['created_at']:
            payload['updated_at'] = payload['created_at']

        return payload

    def process(self, ctxt, publisher_id, event_type, payload, metadata):
        try:
            actions = {
                "dns.domain.create": self.create_or_update,
                "dns.domain.update": self.create_or_update,
                "dns.domain.delete": self.delete,
                "dns.domain.exists": self.create_or_update
            }
            actions[event_type](payload)

            # NOTE: So if this is a initial zone we need to index the SOA / NS
            # records it will have. Let's do this when recieving the create
            # event.
            if event_type == 'dns.domain.create':
                recordsets = designate._get_recordsets(payload['id'])
                for rs in recordsets:
                    rs = designate._serialize_recordset(rs)

                    # So project ID isn't provided in the recordset api.
                    rs['project_id'] = payload['project_id']

                    # TODO(ekarlso,sjmc7): doc_type below should come from
                    # the recordset plugin
                    # registers options
                    self.engine.index(
                        index=self.index_name,
                        doc_type=RecordSetHandler.DOCUMENT_TYPE,
                        body=rs,
                        parent=rs["zone_id"],
                        id=rs["id"])
            return oslo_messaging.NotificationResult.HANDLED
        except Exception as e:
            LOG.exception(e)

    def create_or_update(self, payload):
        payload = self._serialize(payload)

        self.engine.index(
            index=self.index_name,
            doc_type=self.document_type,
            body=payload,
            id=payload["id"]
        )

    def delete(self, payload):
        zone_id = payload['id']

        query = {
            'fields': 'id',
            'query': {
                'term': {
                    'zone_id': zone_id
                }
            }
        }

        documents = helpers.scan(
            client=self.engine,
            index=self.index_name,
            doc_type=self.document_type,
            query=query)

        actions = []
        for document in documents:
            action = {
                '_id': document['_id'],
                '_op_type': 'delete',
                '_index': self.index_name,
                '_type': self.document_type,
                '_parent': zone_id
            }
            actions.append(action)

        if actions:
            helpers.bulk(
                client=self.engine,
                actions=actions)

        try:
            self.engine.delete(
                index=self.index_name,
                doc_type=self.document_type,
                id=zone_id
            )
        except exceptions.NotFoundError:
            msg = "Zone %s not found when deleting"
            LOG.error(msg, zone_id)


class RecordSetHandler(base.NotificationBase):
    # TODO(sjmc7): see note above
    DOCUMENT_TYPE = "OS::Designate::RecordSet"

    def __init__(self, *args, **kwargs):
        super(RecordSetHandler, self).__init__(*args, **kwargs)
        self.record_delete_keys = ['deleted_at', 'deleted',
                                   'attributes']

    def process(self, ctxt, publisher_id, event_type, payload, metadata):
        try:
            actions = {
                "dns.recordset.create": self.create_or_update,
                "dns.recordset.update": self.create_or_update,
                "dns.recordset.delete": self.delete
            }
            actions[event_type](payload)
            return oslo_messaging.NotificationResult.HANDLED
        except Exception as e:
            LOG.exception(e)

    def create_or_update(self, payload):
        id_ = payload['id']
        payload = self._serialize(payload)

        self.engine.index(
            index=self.index_name,
            doc_type=self.document_type,
            body=payload,
            parent=payload["zone_id"],
            id=id_
        )

    def _serialize(self, obj):
        obj['project_id'] = obj.pop('tenant_id')
        obj['zone_id'] = obj.pop('domain_id')
        obj['records'] = [{"data": i["data"]} for i in obj["records"]]
        if not obj['updated_at'] and obj['created_at']:
            obj['updated_at'] = obj['created_at']
        return obj

    def delete(self, payload):
        id_ = payload['id']
        try:
            self.engine.delete(
                index=self.index_name,
                doc_type=self.document_type,
                id=id_
            )
        except exceptions.NotFoundError:
            msg = "RecordSet %s not found when deleting"
            LOG.error(msg, id_)
