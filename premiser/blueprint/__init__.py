import tempfile
from uuid import uuid4
from pathlib import Path
from xml.etree.ElementTree import tostring
from io import BytesIO
from datetime import datetime

from werkzeug.datastructures import FileStorage
from flask import Blueprint, send_file
from flask_restful import Resource, Api, reqparse

from .lib import make_record
from pypremis.nodes import EventIdentifier, Event, EventOutcomeInformation, \
    EventDetailInformation
from pypremis.factories import LinkingObjectIdentifierFactory, \
    LinkingEventIdentifierFactory

BLUEPRINT = Blueprint('premiser', __name__)


BLUEPRINT.config = {}


API = Api(BLUEPRINT)


# RPC-like
class MakePREMIS(Resource):
    def post(self):

        def get_md5(rec):
            obj = rec.get_object_list()[0]
            for objChar in obj.get_objectCharacteristics():
                for fixity in objChar.get_fixity():
                    if fixity.get_messageDigestAlgorithm() == 'md5':
                        return fixity.get_messageDigest()

        def make_fixity_conf_event(rec):
            eventIdentifier = EventIdentifier('uuid4', uuid4().hex)
            event = Event(eventIdentifier, "fixity check",
                          datetime.now().isoformat())
            event.add_eventOutcomeInformation(
                EventOutcomeInformation("success")
            )
            event.add_eventDetailInformation(
                EventDetailInformation(
                    "remote PREMIS generator confirmed md5 checksum matched " +
                    "the checksum provided by the client"
                )
            )
            event.add_linkingObjectIdentifier(
                LinkingObjectIdentifierFactory(
                    rec.get_object_list()[0]
                ).produce_linking_node()
            )
            rec.get_object_list()[0].add_linkingEventIdentifier(
                LinkingEventIdentifierFactory(event).produce_linking_node()
            )
            rec.add_event(event)

        parser = reqparse.RequestParser()
        parser.add_argument(
            "file",
            help="Specify the PREMIS file",
            type=FileStorage,
            location='files',
            required=True
        )
        parser.add_argument(
            "originalName",
            help="Specify the original name of the file as a safely encoded " +
            "string",
            type=str,
            default=None
        )
        parser.add_argument(
            "md5",
            help="Specify an md5 checksum to confirm the integrity of the " +
            "file transfer, if desired.",
            type=str,
            default=None
        )
        args = parser.parse_args()

        tmpdir = tempfile.TemporaryDirectory()
        tmp_file_path = str(Path(tmpdir.name, uuid4().hex))

        args['file'].save(tmp_file_path)

        rec = make_record(tmp_file_path, original_name=args['originalName'])

        if args['md5']:
            if not get_md5(rec) == args['md5']:
                raise ValueError('md5 mismatch!')
            else:
                make_fixity_conf_event(rec)

        rec_str = tostring(rec.to_tree().getroot(), encoding="unicode")

        # Cleanup
        del tmpdir
        # Return the file as an attachment
        return send_file(
            BytesIO(rec_str.encode()),
            attachment_filename="premis.xml"
        )

        # Return the text in some JSON
#       return {"status": "success",
#               "record": tostring(rec.to_tree().getroot(), encoding="unicode")}


@BLUEPRINT.record
def handle_configs(setup_state):
    app = setup_state.app
    BLUEPRINT.config.update(app.config)
    if BLUEPRINT.config.get("tempdir"):
        tempfile.tempdir = BLUEPRINT.config['tempdir']

API.add_resource(MakePREMIS, "/")
