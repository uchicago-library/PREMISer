from os.path import getsize
from mimetypes import guess_type
from uuid import uuid4
from hashlib import md5, sha256
from datetime import datetime
try:
    from magic import from_file
except:
    pass

from pypremis.lib import PremisRecord
from pypremis.nodes import *
from pypremis.factories import LinkingEventIdentifierFactory, \
    LinkingObjectIdentifierFactory

from nothashes import crc32, adler32


__author__ = "Brian Balsamo"
__email__ = "balsamo@uchicago.edu"
__company__ = "The University of Chicago Library"


def produce_checksums(f, hashers, buf=65536):
    data = f.read(buf)
    while data:
        for x in hashers:
            x.update(data)
        data = f.read()
    return {x.name: x.hexdigest() for x in hashers}


def make_record(file_path, original_name=None):
    """
    build a PremisNode.Object from a file and use it to instantiate a record

    __Args__

    1. file_path (str): The full path to a file
    2. item (LDRItem): The LDRItem representative of the file contents

    __Returns__

    1. (PremisRecord): The populated record instance
    """
    obj = _make_object(file_path, original_name)
    rec = PremisRecord(objects=[obj])
    rec.add_event(_make_event())
    _link_obj_and_event(rec)
    return rec


def _link_obj_and_event(rec):
    rec.get_object_list()[0].add_linkingEventIdentifier(
        LinkingEventIdentifierFactory(
            rec.get_event_list()[0]
        ).produce_linking_node()
    )
    rec.get_event_list()[0].add_linkingObjectIdentifier(
        LinkingObjectIdentifierFactory(
            rec.get_object_list()[0]
        ).produce_linking_node()
    )


def _make_event():
    eventIdentifier = EventIdentifier('uuid4', uuid4().hex)
    event = Event(eventIdentifier, "description", datetime.now().isoformat())
    eventDetailInformation = EventDetailInformation(
        "Described via a PREMIS metadata record"
    )
    event.add_eventDetailInformation(eventDetailInformation)
    event.add_eventOutcomeInformation(EventOutcomeInformation("success"))
    return event


def _make_object(file_path, original_name=None):
    """
    make an object entry auto-populated with the required information

    __Args__

    1. file_path (str): The path to the file
    2. item (LDRItem): The LDRItem representative of the file contents

    __Returns__

    1. (PremisRecord.Object): The populated Object... object
    """
    objectIdentifier = _make_objectIdentifier()
    objectCategory = 'file'
    objectCharacteristics = _make_objectCharacteristics(
        file_path, original_name
    )
    obj = Object(objectIdentifier, objectCategory, objectCharacteristics)
    if original_name is not None:
        obj.set_originalName(original_name)
    return obj


def _make_objectIdentifier():
    """
    mint a new object identifier

    __Returns__

    1. (PremisNode.ObjectIdentifier): A populated ObjectIdentifier
    """
    return ObjectIdentifier('uuid4', uuid4().hex)


def _make_objectCharacteristics(file_path, original_name):
    """
    make a new objectCharacteristics node for a file

    __Args__

    1. file_path (str): The path to a file to generate info for
    2. item (LDRItem): The LDRItem representative of the file contents

    __Returns__

    1. (PremisNode.ObjectCharacteristics): a populated ObjectCharacteristics
    node
    """
    fixitys = _make_fixity(file_path)
    size = str(getsize(file_path))
    formats = _make_format(file_path, original_name)
    objChar = ObjectCharacteristics(formats[0])
    if len(formats) > 1:
        for x in formats[1:]:
            objChar.add_format(x)
    for x in fixitys:
        if x is not None:
            objChar.add_fixity(x)
    objChar.set_size(size)
    return objChar


def _make_fixity(file_path):
    """
    make a fixity node for md5 and one for sha256 for a file

    __Args__

    1. file_path (str): The path to a file to generate info for

    __Returns__

    1. fixitys ([PremisNode.Fixity]): fixity nodes including computed
        values
    """
    fixitys = []
    hashers = [md5(), sha256(), crc32(), adler32()]
    hashes = None
    with open(file_path, 'rb') as f:
        hashes = produce_checksums(f, hashers)

    md5_fixity = Fixity('md5', hashes['md5'])
    md5_fixity.set_messageDigestOriginator(
        'python3 hashlib.md5'
    )
    fixitys.append(md5_fixity)

    sha256_fixity = Fixity('sha256', hashes['sha256'])
    sha256_fixity.set_messageDigestOriginator(
        'python3 hashlib.sha256'
    )
    fixitys.append(sha256_fixity)

    crc32_fixity = Fixity('crc32', hashes['crc32'])
    crc32_fixity.set_messageDigestOriginator(
        'python3 zlib.crc32'
    )
    fixitys.append(crc32_fixity)

    adler32_fixity = Fixity('adler32', hashes['adler32'])
    adler32_fixity.set_messageDigestOriginator(
        'python3 zlib.adler32'
    )
    fixitys.append(adler32_fixity)

    return fixitys


def _make_format(file_path, original_name):
    """
    make new format nodes for a file

    __Args__

    1. file_path (str): The path to the file to generate info for
    2. item (LDRItem): The LDRItem representative of the file contents

    __Returns__

    1. (list): a list of format nodes
    """
    magic_num, guess = _detect_mime(file_path, original_name)
    formats = []
    if magic_num:
        premis_magic_format_desig = FormatDesignation(magic_num)
        premis_magic_format = Format(
            formatDesignation=premis_magic_format_desig
        )
        premis_magic_format.set_formatNote(
            'from magic number (python3 magic.from_file)'
        )
        formats.append(premis_magic_format)
    if guess:
        premis_guess_format_desig = FormatDesignation(guess)
        premis_guess_format = Format(
            formatDesignation=premis_guess_format_desig
        )
        premis_guess_format.set_formatNote(
            'from file extension (python3 mimetypes.guess_type)'
        )
        formats.append(premis_guess_format)
    if len(formats) == 0:
        premis_unknown_format_desig = FormatDesignation('undetected')
        premis_unknown_format = Format(
            formatDesignation=premis_unknown_format_desig
        )
        premis_unknown_format.set_formatNote(
            'format detection failed by python3 magic.from_file ' +
            'and mimetypes.guess_type'
        )
        formats.append(premis_unknown_format)
    return formats


def _detect_mime(file_path, original_name):
    """
    use both magic number and file extension mime detection on a file

    __Args__

    1. file_path (str): The path to the file in question
    2. item (LDRItem): The LDRItem representative of the file contents

    __Returns__

    1. (str): magic number mime detected
    2. (str): file extension mime detected
    """
    try:
        magic_num = from_file(file_path, mime=True)
    except:
        magic_num = None
    try:
        guess = guess_type(original_name)[0]
    except:
        guess = None
    return magic_num, guess
